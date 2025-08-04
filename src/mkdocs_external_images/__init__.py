from pathlib import Path

from mkdocs.config import config_options
from mkdocs.config.base import Config
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File, Files


class ExternalImagesPlugin(BasePlugin):
    config_scheme = (
        ("mappings", config_options.ListOfItems(config_options.Type(dict))),
    )

    def on_config(self, config):
        self._mappings = []

        # Process each mapping defined in the configuration
        for mapping in self.config["mappings"]:
            src = Path(mapping["source_dir"]).expanduser().resolve()
            if not src.is_dir():
                raise ValueError(f"[external-images] source_dir not found: {src}")

            target = mapping["target_url_path"].strip("/")
            exts = {
                (e if e.startswith(".") else "." + e).lower()
                for e in mapping["include_exts"]
            }

            self._mappings.append({"src": src, "target": target, "exts": exts})

        print("[external-images] configured mappings:", self._mappings)

        return config

    def on_files(self, files: Files, config):
        # Iterate over all configured mappings
        for mapping in self._mappings:
            src_dir = mapping["src"]
            target_url = mapping["target"]
            allowed_exts = mapping["exts"]

            # Recursively find all allowed files in the source directory
            for file_path in src_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in allowed_exts:
                    # Get the path relative to the source directory
                    relative_path = file_path.relative_to(src_dir)

                    # Construct the destination path in the built site
                    dest_path = f"{target_url}/{relative_path.as_posix()}"

                    # Create a new File object and add it to the collection
                    files.append(
                        File.generated(
                            config=config,
                            src_uri=dest_path,
                            abs_src_path=str(file_path),
                        )
                    )

        return files
