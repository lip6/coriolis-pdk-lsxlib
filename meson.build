
project(
  'coriolis-pdk-lsxlib',
   version: '2026.05.01',
   meson_version: '>= 1.2.0',
)

py       = import( 'python' ).find_installation( pure:false )
py_deps  = dependency( 'python3', required: true )
pdks_dir = py.get_install_dir() / 'pdks' / 'lsxlib'
tech_dir = pdks_dir / 'libs.tech' / 'coriolis'

setup_files = [ 'libs.tech/coriolis/__init__.py'
              , 'libs.tech/coriolis/lsxlib/__init__.py'
              , 'libs.tech/coriolis/lsxlib/techno_symb.py'
              , 'libs.tech/coriolis/lsxlib/lsxlib.py'
              ]
py.install_sources( files(setup_files), subdir:'pdks/lsxlib' )

#install_data  ( 'libs.tech/coriolis/symbolic.graal', install_dir:pdks_dir )
#install_data  ( 'libs.tech/coriolis/symbolic.dreal', install_dir:pdks_dir )
#install_data  ( 'libs.tech/coriolis/sg13g2.rds'    , install_dir:pdks_dir )
install_subdir( 'libs.tech/coriolis/sg13g2'        , install_dir:tech_dir )
install_subdir( 'libs.tech/coriolis/sky130'        , install_dir:tech_dir )
install_subdir( 'libs.ref'                         , install_dir:pdks_dir )
