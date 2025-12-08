# Artifacts Storage (S3-compatible)

- Run MinIO locally:

```
docker run -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin quay.io/minio/minio server /data --console-address :9001
```

- Configure backend via `.env` (see `.env.example`). When `STORAGE_*` is set, `/artifacts/{job_id}/manifest` returns presigned URLs; without it, local FS is used and URLs are served by the backend as before.
