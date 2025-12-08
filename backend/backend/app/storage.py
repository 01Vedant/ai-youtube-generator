"""
Cloud and local storage integration for DevotionalAI Platform
Abstraction layer for S3, Google Cloud Storage, or local filesystem
"""

from abc import ABC, abstractmethod
from pathlib import Path
import shutil
import boto3
import os
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class StorageBackend(ABC):
    """Abstract storage backend"""
    
    @abstractmethod
    def create_project_structure(self, user_id: str, project_id: str):
        """Create project folder structure"""
        pass
    
    @abstractmethod
    def upload_file(self, user_id: str, project_id: str, category: str, file_path: str):
        """Upload file to storage"""
        pass
    
    @abstractmethod
    def download_file(self, user_id: str, project_id: str, category: str, filename: str):
        """Download file from storage"""
        pass
    
    @abstractmethod
    def list_files(self, user_id: str, project_id: str, category: str):
        """List files in category"""
        pass
    
    @abstractmethod
    def delete_project(self, user_id: str, project_id: str):
        """Delete entire project"""
        pass
    
    @abstractmethod
    def get_final_video_path(self, user_id: str, project_id: str):
        """Get path to final video"""
        pass
    
    @abstractmethod
    def get_scene_image_path(self, user_id: str, project_id: str, scene_number: int):
        """Get path to scene image"""
        pass
    
    @abstractmethod
    def get_scene_audio_path(self, user_id: str, project_id: str, scene_number: int):
        """Get path to scene audio"""
        pass
    
    @abstractmethod
    def create_assets_zip(self, user_id: str, project_id: str):
        """Create zip of all assets"""
        pass
    
    @abstractmethod
    def get_download_url(self, user_id: str, project_id: str, file_type: str, expires_in: int = 3600):
        """Get temporary download URL"""
        pass

class LocalStorage(StorageBackend):
    """Local filesystem storage backend"""
    
    def __init__(self):
        self.base_path = Path(settings.LOCAL_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _project_path(self, user_id: str, project_id: str):
        return self.base_path / user_id / project_id
    
    def create_project_structure(self, user_id: str, project_id: str):
        """Create project folder structure"""
        base = self._project_path(user_id, project_id)
        (base / "audio").mkdir(parents=True, exist_ok=True)
        (base / "images").mkdir(parents=True, exist_ok=True)
        (base / "subtitles").mkdir(parents=True, exist_ok=True)
        (base / "prompts").mkdir(parents=True, exist_ok=True)
        (base / "videos").mkdir(parents=True, exist_ok=True)
        logger.info(f"Created project structure: {base}")
    
    def upload_file(self, user_id: str, project_id: str, category: str, file_path: str):
        """Upload file to local storage"""
        dest_dir = self._project_path(user_id, project_id) / category
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        src = Path(file_path)
        dst = dest_dir / src.name
        shutil.copy2(src, dst)
        logger.info(f"Uploaded: {dst}")
        return str(dst)
    
    def download_file(self, user_id: str, project_id: str, category: str, filename: str):
        """Download file from local storage"""
        file_path = self._project_path(user_id, project_id) / category / filename
        return str(file_path) if file_path.exists() else None
    
    def list_files(self, user_id: str, project_id: str, category: str):
        """List files in category"""
        dir_path = self._project_path(user_id, project_id) / category
        return [f.name for f in dir_path.glob("*")] if dir_path.exists() else []
    
    def delete_project(self, user_id: str, project_id: str):
        """Delete entire project"""
        project_path = self._project_path(user_id, project_id)
        if project_path.exists():
            shutil.rmtree(project_path)
            logger.info(f"Deleted project: {project_path}")
    
    def get_final_video_path(self, user_id: str, project_id: str):
        """Get path to final video"""
        video_dir = self._project_path(user_id, project_id) / "videos"
        videos = list(video_dir.glob("final_*.mp4"))
        return str(videos[0]) if videos else None
    
    def get_scene_image_path(self, user_id: str, project_id: str, scene_number: int):
        """Get path to scene image"""
        image_dir = self._project_path(user_id, project_id) / "images"
        images = list(image_dir.glob(f"scene_{scene_number}*"))
        return str(images[0]) if images else None
    
    def get_scene_audio_path(self, user_id: str, project_id: str, scene_number: int):
        """Get path to scene audio"""
        audio_dir = self._project_path(user_id, project_id) / "audio"
        audios = list(audio_dir.glob(f"scene_{scene_number}*"))
        return str(audios[0]) if audios else None
    
    def create_assets_zip(self, user_id: str, project_id: str):
        """Create zip of all assets"""
        project_path = self._project_path(user_id, project_id)
        zip_path = project_path / "assets.zip"
        
        shutil.make_archive(
            str(zip_path.with_suffix("")),
            'zip',
            project_path
        )
        logger.info(f"Created zip: {zip_path}")
        return str(zip_path)
    
    def get_download_url(self, user_id: str, project_id: str, file_type: str, expires_in: int = 3600):
        """Get local file path (not URL)"""
        if file_type == "video":
            return self.get_final_video_path(user_id, project_id)
        elif file_type == "assets":
            return str(self._project_path(user_id, project_id) / "assets.zip")
        return None

class S3Storage(StorageBackend):
    """AWS S3 storage backend"""
    
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket = settings.AWS_S3_BUCKET
    
    def _s3_key(self, user_id: str, project_id: str, category: str = "", filename: str = ""):
        """Build S3 key"""
        parts = [user_id, project_id]
        if category:
            parts.append(category)
        if filename:
            parts.append(filename)
        return "/".join(parts)
    
    def create_project_structure(self, user_id: str, project_id: str):
        """Create project structure markers in S3"""
        categories = ["audio", "images", "subtitles", "prompts", "videos"]
        for cat in categories:
            key = self._s3_key(user_id, project_id, cat, ".keep")
            self.s3.put_object(Bucket=self.bucket, Key=key, Body=b"")
        logger.info(f"Created S3 project structure: {user_id}/{project_id}")
    
    def upload_file(self, user_id: str, project_id: str, category: str, file_path: str):
        """Upload file to S3"""
        filename = Path(file_path).name
        key = self._s3_key(user_id, project_id, category, filename)
        
        self.s3.upload_file(file_path, self.bucket, key)
        logger.info(f"Uploaded to S3: s3://{self.bucket}/{key}")
        return key
    
    def download_file(self, user_id: str, project_id: str, category: str, filename: str):
        """Download file from S3"""
        key = self._s3_key(user_id, project_id, category, filename)
        local_path = f"/tmp/{filename}"
        
        try:
            self.s3.download_file(self.bucket, key, local_path)
            return local_path
        except Exception as e:
            logger.error(f"Failed to download {key}: {e}")
            return None
    
    def list_files(self, user_id: str, project_id: str, category: str):
        """List files in S3 category"""
        prefix = self._s3_key(user_id, project_id, category)
        
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        return [obj["Key"].split("/")[-1] for obj in response.get("Contents", [])]
    
    def delete_project(self, user_id: str, project_id: str):
        """Delete entire project from S3"""
        prefix = self._s3_key(user_id, project_id)
        
        paginator = self.s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                self.s3.delete_object(Bucket=self.bucket, Key=obj["Key"])
        logger.info(f"Deleted S3 project: {prefix}")
    
    def get_final_video_path(self, user_id: str, project_id: str):
        """Get S3 path to final video"""
        return self._s3_key(user_id, project_id, "videos", "final_output.mp4")
    
    def get_scene_image_path(self, user_id: str, project_id: str, scene_number: int):
        """Get S3 path to scene image"""
        return self._s3_key(user_id, project_id, "images", f"scene_{scene_number}.png")
    
    def get_scene_audio_path(self, user_id: str, project_id: str, scene_number: int):
        """Get S3 path to scene audio"""
        return self._s3_key(user_id, project_id, "audio", f"scene_{scene_number}.mp3")
    
    def create_assets_zip(self, user_id: str, project_id: str):
        """Create zip of all assets (would typically be done server-side)"""
        # This would require server-side processing
        # For now, return a marker key
        return self._s3_key(user_id, project_id, "exports", "assets.zip")
    
    def get_download_url(self, user_id: str, project_id: str, file_type: str, expires_in: int = 3600):
        """Get pre-signed S3 download URL"""
        if file_type == "video":
            key = self.get_final_video_path(user_id, project_id)
        elif file_type == "assets":
            key = self.create_assets_zip(user_id, project_id)
        else:
            return None
        
        url = self.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': key},
            ExpiresIn=expires_in
        )
        return url
