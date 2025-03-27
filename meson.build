project('typhoon', meson_version: '>=0.40.1')

py3 = import('python')

# Find Python3 interpreter
python = py3.find_installation()

# Define data directory
data_dir = join_paths(get_option('prefix'), 'share', 'typhoon')

# Install the entire media directory (recursively)
install_subdir('typhoon', install_dir: data_dir)

# Create a wrapper script in /usr/bin
configure_file(
  input: 'typhoon/typhoon_wrapper.in',
  output: 'typhoon',
  configuration: {
    'python': python.full_path(),
    'script': join_paths(data_dir, 'typhoon/typhoon_window.py')
  },
  install: true,
  install_mode: 'rwxr-xr-x',  # Ensure the file is executable
  install_dir: join_paths(get_option('prefix'), 'bin')
)

# Install the desktop file
install_data('typhoon.desktop', install_dir: join_paths(get_option('prefix'), 'share', 'applications'))

# Install the icon to the hicolor directory
install_data('typhoon/typhoon.svg', install_dir: join_paths(get_option('prefix'), 'share', 'icons/hicolor/scalable/apps'))
