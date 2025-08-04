import hashlib
import shutil
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup  # pip install beautifulsoup4
from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from mkdocs.utils import copy_file


class ExternalImagesPlugin(BasePlugin):
    config_scheme = (
        ("source_dir", config_options.Type(str, required=True)),
        ("target_url_path", config_options.Type(str, default="assets")),
        ("include_exts", config_options.Type(list, default=[".png", ".gif"])),
        ("clean_target", config_options.Type(bool, default=True)),
        ("append_hash", config_options.Type(bool, default=False)),
        ("hash_algo", config_options.Type(str, default="sha1")),
    )

    # -------- lifecycle --------
    def on_config(self, config):
        self._src = Path(self.config["source_dir"]).expanduser().resolve()
        if not self._src.is_dir():
            raise ValueError(f"[external-images] source_dir not found: {self._src}")

        self._target = self.config["target_url_path"].strip("/")
        self._site_dir = Path(config["site_dir"]).resolve()

        self._exts = {
            (e if e.startswith(".") else "." + e).lower()
            for e in self.config["include_exts"]
        }

        self._copied = set()  # track rel paths we've already copied
        return config

    def on_pre_build(self, config):
        # Prepare destination root once per build/serve start
        dst_root = self._dst_root()
        if self.config["clean_target"] and dst_root.exists():
            shutil.rmtree(dst_root)
        dst_root.mkdir(parents=True, exist_ok=True)

    def on_serve(self, server, config, builder):
        # Re-render when source images change
        server.watch(str(self._src))
        return server

    # -------- helpers --------
    def _dst_root(self) -> Path:
        return self._site_dir / self._target

    def _is_allowed(self, p: Path) -> bool:
        return p.suffix.lower() in self._exts

    def _asset_url(self, rel: Path) -> str:
        url = f"/{self._target}/{rel.as_posix()}"
        if self.config["append_hash"]:
            h = hashlib.new(self.config["hash_algo"])
            with open(self._src / rel, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            url += f"?v={h.hexdigest()[:12]}"
        return url

    def _copy_on_demand(self, rel: Path):
        """Copy file into site/{target_url_path}/... if not already copied."""
        if rel in self._copied:
            return
        src = self._src / rel
        if not src.exists():
            return
        dst = self._dst_root() / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        copy_file(str(src), str(dst))
        self._copied.add(rel)

    def _maybe_rewrite_relative(self, page, url_str: str):
        """
        If url_str is a relative path that resolves to a file under source_dir
        (ext allowed), copy it immediately and return the public URL; else None.
        """
        if not url_str:
            return None

        parsed = urlparse(url_str)
        if parsed.scheme or parsed.netloc or url_str.startswith("#"):
            return None  # external or anchor

        page_dir = Path(page.file.abs_src_path).parent
        abs_try = (page_dir / url_str).resolve()

        if (
            abs_try.is_file()
            and self._src in abs_try.parents
            and self._is_allowed(abs_try)
        ):
            rel_norm = abs_try.relative_to(self._src)
            self._copy_on_demand(rel_norm)
            return self._asset_url(rel_norm)

        return None

    # -------- rewrite only <img src> and <a href> --------
    def on_page_content(self, html, page, config, files):
        soup = BeautifulSoup(html, "html.parser")

        def rewrite_attr(tag, attr):
            old = tag.get(attr)
            new = self._maybe_rewrite_relative(page, old)
            if new:
                tag[attr] = new

        for img in soup.find_all("img"):
            rewrite_attr(img, "src")

        for a in soup.find_all("a"):
            rewrite_attr(a, "href")

        return str(soup)
