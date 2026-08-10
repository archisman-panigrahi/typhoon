project('typhoon', meson_version: '>=0.59.0')

py3 = import('python')
gnome = import('gnome')

# Find Python3 interpreter
python = py3.find_installation()

# Define data directory
data_dir = join_paths(get_option('prefix'), 'share', 'typhoon')

# Install only the files used by the native Qt Widgets frontend. The legacy
# HTML/CSS/JavaScript WebEngine frontend is intentionally not packaged.
install_data(
  'typhoon/native_window.py',
  'typhoon/chameleon-svgrepo-com.svg',
  'typhoon/clock-exclamation-svgrepo-com.svg',
  'typhoon/dropper-svgrepo-com.svg',
  'typhoon/humidity.svg',
  'typhoon/settings.svg',
  'typhoon/sync.svg',
  install_dir: data_dir
)

# Keep a runtime copy beside native_window.py while also installing the same
# icon into the hicolor theme below.
configure_file(
  input: 'typhoon/io.github.archisman_panigrahi.typhoon.svg',
  output: 'io.github.archisman_panigrahi.typhoon.svg',
  copy: true,
  install: true,
  install_dir: data_dir
)

install_data(
  'typhoon/fonts/Climacons.ttf',
  'typhoon/fonts/ubuntu.ttf',
  install_dir: join_paths(data_dir, 'fonts')
)

# Create a wrapper script in /usr/bin
configure_file(
  input: 'typhoon/typhoon_wrapper.in',
  output: 'typhoon',
  configuration: {
    'python': python.full_path(),
    'script': join_paths(data_dir, 'typhoon/native_window.py')
  },
  install: true,
  install_mode: 'rwxr-xr-x',  # Ensure the file is executable
  install_dir: join_paths(get_option('prefix'), 'bin')
)

# Validate MetaInfo file
metainfo_file = 'io.github.archisman_panigrahi.typhoon.metainfo.xml'
ascli_exe = find_program('appstreamcli', required: false)
if ascli_exe.found()
  test('validate metainfo file',
        ascli_exe,
        args: ['validate',
               '--no-net',
               '--pedantic',
               join_paths(meson.project_source_root(), metainfo_file)]
  )
endif

# Validate desktop file
desktop_file = 'io.github.archisman_panigrahi.typhoon.desktop'
dfv_exe = find_program('desktop-file-validate', required: false)
if dfv_exe.found()
  test('validate desktop file',
        dfv_exe,
        args: [join_paths(meson.project_source_root(), desktop_file)]
  )
endif

# Install the desktop file
install_data('io.github.archisman_panigrahi.typhoon.desktop', install_dir: join_paths(get_option('prefix'), 'share', 'applications'))

# Install the icon to the hicolor directory
install_data('typhoon/io.github.archisman_panigrahi.typhoon.svg', install_dir: join_paths(get_option('prefix'), 'share', 'icons/hicolor/scalable/apps'))

# Install the metainfo file
install_data(
  'io.github.archisman_panigrahi.typhoon.metainfo.xml',
  install_dir: join_paths(get_option('datadir'), 'metainfo')
)

gnome.post_install(
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
