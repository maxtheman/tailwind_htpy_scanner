# Tailwind HTPy Scanner

A utility to scan Python HTPy templates for Tailwind CSS classes and generate a JavaScript file for Tailwind4.0's content configuration.

## Features

- Extracts Tailwind classes from HTPy templates
- Supports ignoring .gitignore
- Supports both class_ keyword arguments and dot notation
- Watch mode for automatic regeneration on file changes
- Generates a JavaScript file compatible with Tailwind's content configuration
- Works with Vite, probably other tools too???

And it has 86% test coverage + works in a (small) production project.

## Installation

Copy this repo and then run

```bash
uv build
```

and use the resultant wheel in your project. Or, just copy main.py over to your project directly.

## Usage

### Command Line

```bash
# Scan specific files
tailwind-htpy-scan --files templates.py other_template.py

# Scan a directory
tailwind-htpy-scan --dir ./templates

# Watch for changes
tailwind-htpy-scan --dir ./templates --watch
```

### In Your Build Process

1. Add the scanner to your build pipeline:

```python
from tailwind_htpy_scanner import scan_directory, generate_template_js
from pathlib import Path

# Scan templates and generate JavaScript file
classes = scan_directory(Path("./templates"))
generate_template_js(classes, Path("./frontend/src/templates.js"))
```

2. Import the generated file in your Vite/webpack entry point:

```javascript
// main.js or similar
import './templates';  // Ensures Tailwind sees these classes
```

or add directly to `vite.config.js`, although this will generate an empty stub in production which is a little goofy.
```javascript
//...
rollupOptions: {
    input: {
        templates: "./src/templates.js",
//...
```

### Integration with Makefile

```makefile
scan-templates:
    tailwind-htpy-scan --files templates.py

watch-templates:
    tailwind-htpy-scan --dir ./templates --watch

dev-all:
    @trap 'kill %1 %2 %3' SIGINT; \
    make watch-templates & \
    make {whatever else you need to do...}
    wait
```

## Development

```bash
# Install development dependencies
uv sync
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT
