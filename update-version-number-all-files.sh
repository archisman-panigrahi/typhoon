#!/bin/bash
# Usage: ./update-version-number-all-files.sh <new_version> "<changelog message>"

set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 <new_version> \"<changelog message>\""
    exit 1
fi

NEW_VERSION="$1"
CHANGELOG="$2"
EMAIL="apandada1@gmail.com"
DATE_RFC2822=$(date -R)
DATE_ISO=$(date +%Y-%m-%d)
DATE_RPM=$(date '+%a %b %d %Y')

# 1. Update fedora-package.spec
if [ -f fedora-package.spec ]; then
    sed -i "s/^Version:\s*[0-9.]\+/Version:        $NEW_VERSION/" fedora-package.spec
    
    # Update changelog in spec file
    CHANGELOG_ENTRY="* $DATE_RPM Archisman Panigrahi <$EMAIL> - $NEW_VERSION-1
- $CHANGELOG
"
    # Insert after %changelog line
    awk -v entry="$CHANGELOG_ENTRY" '
        /^%changelog/ && !x {print; print entry; x=1; next} 1
    ' fedora-package.spec > fedora-package.spec.tmp && mv fedora-package.spec.tmp fedora-package.spec
    
    echo "Updated fedora-package.spec and its changelog"
fi

# 2. Update typhoon/typhoon.html
if [ -f typhoon/typhoon.html ]; then
    sed -i "s|\(<h1 style=\"text-align: center\"><a href=\"https://archisman-panigrahi.github.io/typhoon\">Typhoon</a> \)[0-9.]\+\(</h1>\)|\1$NEW_VERSION\2|" typhoon/typhoon.html
    echo "Updated typhoon/typhoon.html"
fi

# 3. Update debian/changelog
if [ -f debian/changelog ]; then
    PACKAGE=$(head -1 debian/changelog | awk '{print $1}')
    {
        echo "$PACKAGE ($NEW_VERSION) noble; urgency=medium"
        echo
        echo "  * $CHANGELOG"
        echo
        echo " -- Archisman Panigrahi <$EMAIL>  $DATE_RFC2822"
        echo
        cat debian/changelog
    } > debian/changelog.new && mv debian/changelog.new debian/changelog
    echo "Updated debian/changelog"
fi

# 4. Update io.github.archisman_panigrahi.typhoon.metainfo.xml
METAINFO="io.github.archisman_panigrahi.typhoon.metainfo.xml"
if [ -f "$METAINFO" ]; then
    RELEASE_ENTRY="  <release version=\"$NEW_VERSION\" date=\"$DATE_ISO\">
      <url type=\"details\">https://github.com/archisman-panigrahi/typhoon/releases/tag/v$NEW_VERSION</url>
      <description>
        <ul>
          <li>$CHANGELOG</li>
        </ul>
      </description>
  </release>"
    # Insert after <releases>
    awk -v entry="$RELEASE_ENTRY" '
        /<releases>/ && !x {print; print entry; x=1; next} 1
    ' "$METAINFO" > "$METAINFO.tmp" && mv "$METAINFO.tmp" "$METAINFO"
    echo "Updated $METAINFO"
fi

# # 5. Update snap/snapcraft.yaml
# if [ -f snap/snapcraft.yaml ]; then
#     sed -i "s/source-tag: 'v[0-9.]\+'/source-tag: 'v$NEW_VERSION'/" snap/snapcraft.yaml
#     echo "Updated snap/snapcraft.yaml"
# fi

# 6. Update aur/PKGBUILD
if [ -f aur/PKGBUILD ]; then
    sed -i "s/^pkgver=.*/pkgver=$NEW_VERSION/" aur/PKGBUILD
    echo "Updated aur/PKGBUILD"
fi

echo "All done. Version updated to $NEW_VERSION."
