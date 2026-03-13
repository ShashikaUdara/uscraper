#!/bin/sh
# Install system dependencies for uscraper on Ubuntu/Debian.
# Run with: sudo scripts/install_deps_ubuntu.sh

set -e

echo "Installing system packages for uscraper..."
apt-get update
apt-get install -y \
  python3 \
  python3-venv \
  python3-tk \
  python3-pip

echo "System packages installed."
echo ""
echo "Next steps (as your user, from project root):"
echo "  make venv"
echo "  make install"
echo "  make install-deps   # Playwright system libs (uses pip/playwright)"
echo "  make install-browsers   # Optional: download browsers"
echo "  make run"
