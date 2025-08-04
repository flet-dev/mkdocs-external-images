# mkdocs-external-images

A MkDocs plugin that lets you reference and publish files from directories outside `docs_dir` by mapping them into a path within the generated site.

Configuring in `mkdocs.yml`:

```yaml
plugins:
  - external-images:
      mappings:
        - source_dir: ../../examples
          target_url_path: examples
          include_exts: [".png", ".gif"]
        # - source_dir: /Documents/movies
        #   target_url_path: movies
        #   include_exts: [".mp4", ".avi"]
```
