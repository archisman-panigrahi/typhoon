# COPR Build Setup for Typhoon

This guide will help you set up and build Typhoon packages on Fedora's COPR (Cool Other Package Repo) service.

## Prerequisites

1. **Fedora COPR Account**: Create an account at https://copr.fedorainfracloud.org/
2. **Install Required Tools**:
   ```bash
   sudo dnf install copr-cli rpm-build rpmdevtools
   ```

## Step 1: Configure COPR CLI

1. Get your API token from https://copr.fedorainfracloud.org/api/
2. Save it to `~/.config/copr`:
   ```bash
   mkdir -p ~/.config
   # The COPR website provides the exact content to save
   ```

## Step 2: Create Your COPR Project

1. Go to https://copr.fedorainfracloud.org/
2. Click "New Project"
3. Fill in the details:
   - **Name**: `typhoon` (or your preferred name)
   - **Description**: `Stylish weather application powered by Open-Meteo`
   - **Instructions**: Link to the GitHub repo
   - **Chroots**: Select Fedora versions you want to build for (e.g., Fedora 39, 40, 41, Rawhide)
   - **Build Dependencies**: Leave empty (dependencies are in the spec file)
   - **Enable Internet**: Yes (for downloading source tarball)

Or create it via CLI:
```bash
copr-cli create typhoon \
  --chroot fedora-39-x86_64 \
  --chroot fedora-40-x86_64 \
  --chroot fedora-41-x86_64 \
  --chroot fedora-rawhide-x86_64 \
  --description "Stylish weather application powered by Open-Meteo" \
  --instructions "https://github.com/archisman-panigrahi/typhoon"
```

## Step 3: Build the Package

### Method 1: Build from SRPM (Recommended)

1. Generate the source RPM:
   ```bash
   make srpm
   ```

2. Upload to COPR:
   ```bash
   copr-cli build typhoon ~/rpmbuild/SRPMS/typhoon-1.7.0-1.*.src.rpm
   ```

### Method 2: Build from Git (Automated)

You can also configure COPR to build automatically from your Git repository:

1. In your COPR project settings, go to "Packages" → "New Package" → "SCM"
2. Fill in:
   - **Package name**: `typhoon`
   - **Clone URL**: `https://github.com/archisman-panigrahi/typhoon.git`
   - **Subdirectory**: (leave empty)
   - **Spec File**: `fedora-package.spec`
   - **Type**: `git`
   - **Branch/Tag**: `v1.7.0` (or `main` for automatic builds)

3. Click "Create" and then "Build"

### Method 3: Build from URL

```bash
copr-cli buildscm typhoon \
  --clone-url https://github.com/archisman-panigrahi/typhoon.git \
  --commit v1.7.0 \
  --spec fedora-package.spec \
  --type git
```

## Step 4: Monitor Build Status

Check build status:
```bash
copr-cli watch-build <build-id>
```

Or visit: https://copr.fedorainfracloud.org/coprs/<your-username>/typhoon/builds/

## Step 5: Installing Your COPR Package

Once the build succeeds, users can install Typhoon from your COPR repo:

```bash
sudo dnf copr enable <your-username>/typhoon
sudo dnf install typhoon
```

## Updating the Package

When you release a new version:

1. Update the version in `fedora-package.spec`:
   ```spec
   Version:        1.8.0
   ```

2. Add changelog entry:
   ```spec
   %changelog
   * Sat Feb 23 2026 Your Name <your@email.com> - 1.8.0-1
   - Update to version 1.8.0
   - Add description of changes
   ```

3. Tag the release:
   ```bash
   git tag v1.8.0
   git push origin v1.8.0
   ```

4. Rebuild:
   ```bash
   make srpm
   copr-cli build typhoon ~/rpmbuild/SRPMS/typhoon-1.8.0-1.*.src.rpm
   ```

## Automatic Builds with Webhooks

You can set up automatic builds on new releases:

1. In COPR project settings, go to "Settings" → "Webhooks"
2. Get the webhook URL
3. In GitHub repo settings, add webhook:
   - **Payload URL**: (COPR webhook URL)
   - **Content type**: `application/json`
   - **Events**: Select "Releases"

Now COPR will automatically rebuild when you create a GitHub release!

## Troubleshooting

### Build fails with "Source not found"
- Ensure the git tag exists and matches the Version in the spec file
- Check that the Source0 URL is accessible

### Build fails with missing dependencies
- Add missing BuildRequires or Requires to the spec file
- Ensure the dependency is available in standard Fedora repos or enable additional repos

### Permission denied when uploading
- Check your COPR API token in `~/.config/copr`
- Ensure you have write access to the COPR project

## Resources

- **COPR Documentation**: https://docs.pagure.org/copr.copr/
- **Fedora Packaging Guidelines**: https://docs.fedoraproject.org/en-US/packaging-guidelines/
- **RPM Spec File Reference**: https://rpm-packaging-guide.github.io/

## Repository Information

Your COPR repository URL will be:
```
https://copr.fedorainfracloud.org/coprs/<your-username>/typhoon/
```

Share this with users so they can easily install Typhoon on Fedora!
