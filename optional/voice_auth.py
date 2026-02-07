import os
import logging
import json
import numpy as np
import torch
from modules.logger import app_logger

# Lazy loading to avoid heavy imports if not used
try:
    from pyannote.audio import Model, Inference
    from scipy.spatial.distance import cdist
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    app_logger.warning("Optional Dependency 'pyannote.audio' not found. Voice Auth will be disabled.")

class VoiceAuthSkill:
    def __init__(self, core):
        self.core = core
        self.config_manager = core.config_manager
        self.enabled = False
        self.inference = None
        self.profiles = {}
        self.permissions = {}
        
        # Load Config
        self.data_dir = "data/biometrics"
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.permissions_file = "config/permissions.json"
        
        if PYANNOTE_AVAILABLE:
            self.setup_model()
            self.load_profiles()
            self.load_permissions()
            self.enabled = True
            app_logger.info("[OK] VoiceAuthSkill initialized (Optional).")
        else:
            app_logger.warning("VoiceAuthSkill disabled due to missing dependencies.")

    def setup_model(self):
        """Load pretrained speaker embedding model."""
        try:
            
            auth_token = os.environ.get("HF_TOKEN") # Or config
            
            app_logger.info("Loading Voice Biometrics Model (this may take a while)...")
            self.model = Model.from_pretrained("pyannote/embedding", use_auth_token=auth_token)
            self.inference = Inference(self.model, window="whole")
            app_logger.info("Voice Biometrics Model loaded.")
            
        except Exception as e:
            app_logger.error(f"Failed to load Voice Biometrics Model: {e}")
            self.enabled = False

    def load_profiles(self):
        """Load user voice profiles from disk."""
        try:
            files = os.listdir(self.data_dir)
            for f in files:
                if f.endswith(".npy"):
                    user = f.replace(".npy", "")
                    path = os.path.join(self.data_dir, f)
                    self.profiles[user] = np.load(path)
            app_logger.info(f"Loaded {len(self.profiles)} voice profiles.")
        except Exception as e:
            app_logger.error(f"Error loading voice profiles: {e}")

    def load_permissions(self):
        """Load permissions from JSON."""
        if os.path.exists(self.permissions_file):
            try:
                with open(self.permissions_file, 'r') as f:
                    self.permissions = json.load(f)
            except Exception as e:
                app_logger.error(f"Error loading permissions: {e}")
        else:
            # Default defaults
            self.permissions = {
                "roles": {
                    "admin": ["*"],
                    "guest": ["time", "weather", "music"]
                },
                "users": {
                    "admin": "admin" # Default admin user
                }
            }
            # Write default
            try:
                with open(self.permissions_file, 'w') as f:
                    json.dump(self.permissions, f, indent=4)
            except:
                pass

    def enroll_user(self, user_name, audio_buffer):
        """Create a profile for a user from audio buffer."""
        if not self.enabled or not self.inference:
            return False, "Voice Auth not enabled."
            
        try:
            # Convert buffer (deque of bytes) to tensor
            # audio_buffer is raw PCM 16-bit 16kHz Mono
            # PyAnnote expects (channels, time) tensor
            
            # 1. Join bytes
            raw_data = b''.join(audio_buffer)
            # 2. Convert to float32 [-1, 1]
            audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # 3. Reshape to (1, samples)
            waveform = torch.from_numpy(audio_np).unsqueeze(0)
            
            # 4. Extract embedding
            embedding = self.inference({"waveform": waveform, "sample_rate": 16000})
            
            # 5. Save
            path = os.path.join(self.data_dir, f"{user_name}.npy")
            np.save(path, embedding)
            
            self.profiles[user_name] = embedding
            return True, f"Profile created for {user_name}."
            
        except Exception as e:
            app_logger.error(f"Enrollment failed: {e}")
            return False, str(e)

    def identify_speaker(self, audio_buffer):
        """Identify user from audio buffer."""
        if not self.enabled or not self.profiles:
            return "unknown", 0.0
            
        try:
            # Process Audio
            raw_data = b''.join(audio_buffer)
            audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
            waveform = torch.from_numpy(audio_np).unsqueeze(0)
            
            embedding = self.inference({"waveform": waveform, "sample_rate": 16000})
            
            best_score = 100.0 # Distance (lower is better for cdist cosine)
            best_user = "unknown"
            
            # Compare with profiles (Cosine Distance)
            for user, profile in self.profiles.items():
                # Profile shape (D,), Embedding shape (D,)
                # spatial.distance.cosine returns 1 - cos_sim
                dist = cdist(embedding.reshape(1, -1), profile.reshape(1, -1), metric="cosine")[0][0]
                
                if dist < best_score:
                    best_score = dist
                    best_user = user
            
            # Threshold (Cosine distance 0.0 = identical, 2.0 = opposite, usually < 0.7 is good match)
            # We convert to confidence 0-1 approx
            confidence = max(0, 1 - best_score)
            
            app_logger.info(f"Speaker ID: {best_user} (Dist: {best_score:.4f}, Conf: {confidence:.2f})")
            
            if best_score < 0.6: # Configurable threshold
                return best_user, confidence
            else:
                return "unknown", confidence
                
        except Exception as e:
            app_logger.error(f"Identification failed: {e}")
            return "unknown", 0.0

    def check_permission(self, user, command_type):
        """Check if user has permission for command type."""
        # 1. Get Role
        user_role = self.permissions.get("users", {}).get(user, "guest")
        
        # 2. Get Role Permissions
        allowed = self.permissions.get("roles", {}).get(user_role, [])
        
        if "*" in allowed:
            return True
            
        if command_type in allowed:
            return True
            
        return False
