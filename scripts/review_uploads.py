from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


PENDING_METADATA_PREFIX = "pending/metadata/"
PENDING_UPLOAD_PREFIX = "pending/uploads/"


@dataclass(frozen=True)
class R2Settings:
    endpoint: str
    bucket: str
    access_key_id: str
    secret_access_key: str


@dataclass(frozen=True)
class R2Object:
    key: str
    size: int
    last_modified: str = ""


class R2Error(RuntimeError):
    pass


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        raise FileNotFoundError(f"找不到环境文件：{path}")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip().strip('"').strip("'")
    return values


def load_settings(env_file: Path | None = None) -> R2Settings:
    values = dict(os.environ)
    if env_file:
        values.update(parse_env_file(env_file))

    endpoint = values.get("R2_ENDPOINT", "").strip()
    bucket = (values.get("R2_BUCKET") or values.get("R2_BUCKET_NAME") or "").strip()
    access_key_id = values.get("R2_ACCESS_KEY_ID", "").strip()
    secret_access_key = values.get("R2_SECRET_ACCESS_KEY", "").strip()

    missing = [
        name
        for name, value in {
            "R2_ENDPOINT": endpoint,
            "R2_BUCKET": bucket,
            "R2_ACCESS_KEY_ID": access_key_id,
            "R2_SECRET_ACCESS_KEY": secret_access_key,
        }.items()
        if not value
    ]
    if missing:
        raise R2Error("缺少必要环境变量：" + "、".join(missing))

    return R2Settings(
        endpoint=normalise_endpoint(endpoint, bucket),
        bucket=bucket,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
    )


def normalise_endpoint(endpoint: str, bucket: str) -> str:
    parsed = urllib.parse.urlsplit(endpoint.rstrip("/"))
    if not parsed.scheme or not parsed.netloc:
        raise R2Error("R2_ENDPOINT 格式不正确")
    path = parsed.path.strip("/")
    if path == bucket:
        path = ""
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, f"/{path}" if path else "", "", "")).rstrip("/")


def pending_metadata_key(request_id: str) -> str:
    clean_id = clean_request_id(request_id)
    return f"{PENDING_METADATA_PREFIX}{clean_id}.json"


def pending_upload_prefix(request_id: str) -> str:
    clean_id = clean_request_id(request_id)
    return f"{PENDING_UPLOAD_PREFIX}{clean_id}/"


def clean_request_id(request_id: str) -> str:
    value = request_id.strip()
    if not value or any(char in value for char in "/\\"):
        raise R2Error("request_id 不正确")
    return value.removesuffix(".json")


def request_id_from_metadata_key(key: str) -> str:
    if not key.startswith(PENDING_METADATA_PREFIX) or not key.endswith(".json"):
        raise R2Error(f"不是待审核 metadata key：{key}")
    return key.removeprefix(PENDING_METADATA_PREFIX).removesuffix(".json")


class R2S3Client:
    def __init__(self, settings: R2Settings) -> None:
        self.settings = settings
        self._parsed_endpoint = urllib.parse.urlsplit(settings.endpoint)

    def list_objects(self, prefix: str) -> list[R2Object]:
        body = self._request(
            "GET",
            query={
                "list-type": "2",
                "prefix": prefix,
            },
        )
        return parse_list_objects(body)

    def get_text(self, key: str) -> str:
        body = self._request("GET", key=key)
        return body.decode("utf-8")

    def delete_object(self, key: str) -> None:
        self._request("DELETE", key=key)

    def _request(
        self,
        method: str,
        key: str = "",
        query: dict[str, str] | None = None,
        body: bytes = b"",
    ) -> bytes:
        query = query or {}
        now = dt.datetime.now(dt.timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(body).hexdigest()

        path = "/" + urllib.parse.quote(self.settings.bucket, safe="")
        if key:
            path += "/" + urllib.parse.quote(key, safe="/~")

        canonical_query = canonical_query_string(query)
        host = self._parsed_endpoint.netloc
        headers = {
            "host": host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        signed_headers = ";".join(sorted(headers))
        canonical_headers = "".join(f"{name}:{headers[name]}\n" for name in sorted(headers))
        canonical_request = "\n".join(
            [
                method,
                path,
                canonical_query,
                canonical_headers,
                signed_headers,
                payload_hash,
            ]
        )

        credential_scope = f"{date_stamp}/auto/s3/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )
        signing_key = derive_signing_key(self.settings.secret_access_key, date_stamp)
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        headers["authorization"] = (
            "AWS4-HMAC-SHA256 "
            f"Credential={self.settings.access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        url = urllib.parse.urlunsplit(
            (
                self._parsed_endpoint.scheme,
                host,
                path,
                canonical_query,
                "",
            )
        )
        request = urllib.request.Request(url, data=body if body else None, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise R2Error(f"R2 请求失败：HTTP {error.code} {detail}") from error
        except urllib.error.URLError as error:
            raise R2Error(f"R2 请求失败：{error.reason}") from error


def canonical_query_string(query: dict[str, str]) -> str:
    parts = [
        (
            urllib.parse.quote(str(name), safe="-_.~"),
            urllib.parse.quote(str(value), safe="-_.~"),
        )
        for name, value in query.items()
    ]
    return "&".join(f"{name}={value}" for name, value in sorted(parts))


def derive_signing_key(secret: str, date_stamp: str) -> bytes:
    date_key = hmac.new(("AWS4" + secret).encode("utf-8"), date_stamp.encode("utf-8"), hashlib.sha256).digest()
    region_key = hmac.new(date_key, b"auto", hashlib.sha256).digest()
    service_key = hmac.new(region_key, b"s3", hashlib.sha256).digest()
    return hmac.new(service_key, b"aws4_request", hashlib.sha256).digest()


def parse_list_objects(xml_body: bytes) -> list[R2Object]:
    root = ET.fromstring(xml_body)
    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag.split("}", 1)[0] + "}"

    objects: list[R2Object] = []
    for item in root.findall(f"{namespace}Contents"):
        key = item.findtext(f"{namespace}Key", default="")
        size_text = item.findtext(f"{namespace}Size", default="0")
        modified = item.findtext(f"{namespace}LastModified", default="")
        if key:
            objects.append(R2Object(key=key, size=int(size_text or "0"), last_modified=modified))
    return objects


def load_metadata(client: R2S3Client, request_id: str) -> dict[str, object]:
    text = client.get_text(pending_metadata_key(request_id))
    return json.loads(text)


def format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 / 1024:.1f} MB"


def list_pending(client: R2S3Client) -> int:
    metadata_objects = client.list_objects(PENDING_METADATA_PREFIX)
    if not metadata_objects:
        print("没有待审核上传。")
        return 0

    print(f"待审核上传：{len(metadata_objects)} 条")
    for item in metadata_objects:
        request_id = request_id_from_metadata_key(item.key)
        try:
            metadata = load_metadata(client, request_id)
        except Exception as error:  # noqa: BLE001 - 管理脚本要继续列出其他记录
            print(f"- {request_id}  metadata 读取失败：{error}")
            continue

        title = str(metadata.get("title") or "未填书名")
        author = str(metadata.get("author") or "未填作者")
        filename = str(metadata.get("filename") or "")
        size = metadata.get("size")
        size_label = format_size(int(size)) if isinstance(size, int) else "未知大小"
        print(f"- {request_id}  {title}｜{author}｜{filename}｜{size_label}")
    return 0


def show_pending(client: R2S3Client, request_id: str) -> int:
    metadata = load_metadata(client, request_id)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    uploads = client.list_objects(pending_upload_prefix(request_id))
    if uploads:
        print("\n文件：")
        for item in uploads:
            print(f"- {item.key} ({format_size(item.size)})")
    return 0


def delete_pending(client: R2S3Client, request_id: str, yes: bool) -> int:
    keys = [pending_metadata_key(request_id)]
    keys.extend(item.key for item in client.list_objects(pending_upload_prefix(request_id)))
    if not yes:
        print("将删除以下对象：")
        for key in keys:
            print(f"- {key}")
        print("\n确认删除请加 --yes。")
        return 1

    for key in keys:
        client.delete_object(key)
        print(f"已删除：{key}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="管理 R2 pending 区的上传审核记录。")
    parser.add_argument("--env-file", type=Path, help="本地 .env 文件路径；不传则读取当前环境变量。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="列出待审核上传。")

    show_parser = subparsers.add_parser("show", help="查看一条待审核记录。")
    show_parser.add_argument("request_id", help="提交 ID。")

    delete_parser = subparsers.add_parser("delete", help="删除一条待审核记录及其文件。")
    delete_parser.add_argument("request_id", help="提交 ID。")
    delete_parser.add_argument("--yes", action="store_true", help="确认删除。")

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        settings = load_settings(args.env_file)
        client = R2S3Client(settings)
        if args.command == "list":
            return list_pending(client)
        if args.command == "show":
            return show_pending(client, args.request_id)
        if args.command == "delete":
            return delete_pending(client, args.request_id, args.yes)
    except R2Error as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
