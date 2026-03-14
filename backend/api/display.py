import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import schemas
import security
from crud import display_crud
from database import get_db
from media_storage import (
    InvalidMediaAssetError,
    delete_storage_path,
    normalize_media_kind,
    resolve_storage_path,
    save_upload,
    storage_path_exists,
)


router = APIRouter(
    tags=["Display"],
)


@router.get(
    "/display/taps/{tap_id}/snapshot",
    response_model=schemas.DisplayTapSnapshot,
    dependencies=[Depends(security.get_display_reader)],
)
def get_display_tap_snapshot(tap_id: int, request: Request, db: Session = Depends(get_db)):
    snapshot = display_crud.build_display_snapshot(
        db,
        tap_id=tap_id,
        content_url_builder=lambda asset_id: str(request.url_for("get_media_asset_content", asset_id=asset_id)),
    )
    etag = f'"{snapshot.content_version}"'
    if display_crud.is_not_modified(
        request.headers.get("if-none-match"),
        current_content_version=snapshot.content_version,
    ):
        return Response(status_code=304, headers={"ETag": etag})

    return Response(
        content=snapshot.model_dump_json(by_alias=True),
        media_type="application/json",
        headers={"ETag": etag},
    )


@router.post(
    "/media-assets",
    response_model=schemas.MediaAssetCreateResponse,
    status_code=201,
    dependencies=[Depends(security.get_current_user)],
)
def upload_media_asset(
    request: Request,
    kind: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    asset_id = uuid.uuid4()
    try:
        stored = save_upload(
            file.file,
            filename=file.filename or f"{asset_id}",
            content_type=file.content_type,
            asset_id=asset_id,
            kind=kind,
        )
    except InvalidMediaAssetError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    try:
        asset = display_crud.create_media_asset(
            db,
            asset_id=asset_id,
            kind=stored["kind"],
            original_filename=file.filename or stored["storage_key"],
            mime_type=stored["mime_type"],
            storage_key=stored["storage_key"],
            byte_size=stored["byte_size"],
            checksum_sha256=stored["checksum_sha256"],
            width=stored["width"],
            height=stored["height"],
        )
    except Exception:
        db.rollback()
        delete_storage_path(stored["storage_key"])
        raise

    return display_crud.serialize_created_media_asset(
        asset,
        content_url=str(request.url_for("get_media_asset_content", asset_id=asset.asset_id)),
    )


@router.get(
    "/media-assets",
    response_model=list[schemas.MediaAssetListItem],
    dependencies=[Depends(security.get_current_user)],
)
def get_media_assets(request: Request, kind: str | None = None, db: Session = Depends(get_db)):
    if kind is not None:
        try:
            kind = normalize_media_kind(kind)
        except InvalidMediaAssetError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    assets = display_crud.list_media_assets(db, kind=kind)
    return [
        display_crud.serialize_media_asset(
            asset,
            content_url=str(request.url_for("get_media_asset_content", asset_id=asset.asset_id)),
        )
        for asset in assets
    ]


@router.get(
    "/media-assets/{asset_id}/content",
    name="get_media_asset_content",
    dependencies=[Depends(security.get_display_reader)],
)
def get_media_asset_content(asset_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    asset = display_crud.get_media_asset(db, asset_id)
    etag = f'"{asset.checksum_sha256}"'
    if display_crud.is_not_modified(request.headers.get("if-none-match"), current_content_version=asset.checksum_sha256):
        return Response(status_code=304, headers={"ETag": etag})

    if not storage_path_exists(asset.storage_key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset file is missing")

    path = resolve_storage_path(asset.storage_key)
    return FileResponse(
        path,
        media_type=asset.mime_type,
        filename=asset.original_filename,
        headers={
            "ETag": etag,
            "Cache-Control": "public, max-age=31536000, immutable",
        },
    )
