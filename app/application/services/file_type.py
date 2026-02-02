from fastapi import HTTPException, status, UploadFile

ALLOWED_FILE_TYPES = [
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]


def validate_file_type(uploaded_file: UploadFile):
    if uploaded_file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid file format",
                "filename": uploaded_file.filename,
                "received_content_type": uploaded_file.content_type,
                "allowed_types": ALLOWED_FILE_TYPES,
                "message": "Please upload a file matching one of the allowed formats."
            }
        )
