#!/bin/bash
# Quick setup script for COPR build environment

set -e

echo "========================================"
echo "Typhoon COPR Build Environment Setup"
echo "========================================"
echo ""

# Check if running on Fedora/RHEL-based system
if ! command -v dnf &> /dev/null; then
    echo "❌ This script requires a Fedora/RHEL-based system with dnf"
    exit 1
fi

echo "📦 Installing required packages..."
sudo dnf install -y copr-cli rpm-build rpmdevtools spectool

echo ""
echo "📁 Setting up RPM build directories..."
rpmdev-setuptree

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Configure COPR CLI with your API token:"
echo "   Get your token from: https://copr.fedorainfracloud.org/api/"
echo "   Save it to: ~/.config/copr"
echo ""
echo "2. Create a COPR project:"
echo "   Visit: https://copr.fedorainfracloud.org/"
echo "   Or use: copr-cli create typhoon --chroot fedora-40-x86_64"
echo ""
echo "3. Build the source RPM:"
echo "   make srpm"
echo ""
echo "4. Upload to COPR:"
echo "   copr-cli build <your-project-name> ~/rpmbuild/SRPMS/typhoon-*.src.rpm"
echo ""
echo "📖 For detailed instructions, see: COPR_BUILD_GUIDE.md"
