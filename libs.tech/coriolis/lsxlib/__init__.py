
from pathlib import Path
from coriolis.helpers.io         import ErrorMessage, vprint
from coriolis.designflow.technos import Where
from coriolis.designflow.task    import ShellEnv


__all__ = [ 'setup', 'USE_REAL_RDS' ]


USE_REAL_RDS = 0x0001


def setup ( techno=None, flags=0 ):
    if techno is None:
        raise ErrorMessage( 1, 'lsxlib.setup(): <techno> argument has not been set.' )

    from coriolis                     import Cfg 
    from coriolis                     import Viewer
    from coriolis                     import CRL 
    from coriolis.helpers             import overlay, l, u, n
    from coriolis.designflow.yosys    import Yosys
    from coriolis.designflow.iverilog import Iverilog
    from coriolis.designflow.klayout  import Klayout
    from coriolis.designflow.lvx      import Lvx
    from coriolis.designflow.x2y      import x2y
    from coriolis.designflow.tasyagle import TasYagle
#   from .designflow.drc              import DRC
#   from .techno                      import setup as techno_setup 
#   from .StdCellLib                  import setup as StdCellLib_setup
    
    with overlay.CfgCache(priority=Cfg.Parameter.Priority.UserFile) as cfg:
        cfg.misc.catchCore     = False
        cfg.misc.minTraceLevel = 12300
        cfg.misc.maxTraceLevel = 12400
        cfg.misc.info          = False
        cfg.misc.paranoid      = False
        cfg.misc.bug           = False
        cfg.misc.logMode       = True
        cfg.misc.verboseLevel1 = True
        cfg.misc.verboseLevel2 = True

    isPdkInstalled = True if Path(__file__).parents[1].name == 'pdks' else False
    vprint( 1,  '  o  Setup LSxLib library.' )
    vprint( 1, f'     - Target technology: "{techno}".' )
    vprint( 1, f'     - PDK installed:     "{isPdkInstalled}".' )

    if   techno == 'ihpsg13g2': pass
    elif techno == 'sky130':    pass
    else:
        raise ErrorMessage( 1, f'lsxlib.setup(): techno="{techno}" is not supported.' )
    if isPdkInstalled: realTechnoDir = Path( __file__ ).parent / 'libs.tech' / 'coriolis' / techno
    else:              realTechnoDir = Path( __file__ ).parent / techno
    if not realTechnoDir.is_dir():
        raise ErrorMessage( 1, [ f'lsxlib.setup(): techno="{techno}" directory is missing.'
                               , f'({realTechnoDir})' ] )

    Where()

    ShellEnv.RDS_TECHNO_NAME = (realTechnoDir / 'symbolic.rds').as_posix()
    if flags & USE_REAL_RDS:
        ShellEnv.RDS_TECHNO_NAME = (realTechnoDir / f'{techno}_lsx.rds').as_posix()
    ShellEnv.GRAAL_TECHNO_NAME = (realTechnoDir / 'symbolic.graal').as_posix()
   #ShellEnv.DREAL_TECHNO_NAME = (realTechnoDir / 'symbolic.dreal').as_posix()
    ShellEnv.MBK_SPI_MODEL     = (realTechnoDir / 'spimodel.cfg'  ).as_posix()

#   techno_setup()
#   StdCellLib_setup()

#   liberty        = pdkMasterTop / 'libs.ref' / 'StdCellLib' / 'liberty' / 'StdCellLib_nom.lib'
#   stdCellLibVlog = pdkMasterTop / 'libs.ref' / 'StdCellLib' / 'verilog' / 'StdCellLib.v'
#   spiceCells     = pdkMasterTop / 'libs.ref' / 'StdCellLib' / 'spice'
#   ngspiceTech    = pdkIHPTop    / 'libs.tech' / 'ngspice'
#   verilogATech   = pdkIHPTop    / 'libs.tech' / 'verilog-a'
#   klayoutTech    = pdkIHPTop    / 'libs.tech' / 'klayout'
#   klayoutHome    = Path().home() / '.klayout'
#   kdrcScript     = klayoutTech  / 'tech' / 'drc' / 'run_drc.py'
#   lypFile        = klayoutTech  / 'tech' / 'sg13g2.lyp'
#   fillerScript   = klayoutTech  / 'tech' / 'scripts' / 'filler.py'
#   sealRingScript = klayoutTech  / 'tech' / 'scripts' / 'sealring.py'
#   
#   with overlay.CfgCache(priority=Cfg.Parameter.Priority.UserFile) as cfg:
#       cfg.etesian.graphics    = 3
#       cfg.etesian.spaceMargin = 0.10
#       cfg.katana.eventsLimit  = 4000000
#       af  = CRL.AllianceFramework.get()
#       lg5 = af.getRoutingGauge('StdCellLib').getLayerGauge( 5 )
#       lg5.setType( CRL.RoutingLayerGauge.PowerSupply )
#       env = af.getEnvironment()
#       env.setCLOCK( '^sys_clk$|^ck|^jtag_tck$' )
#       env.setSCALE_X( 100 )

#   Yosys.setLiberty( liberty )
#   shellEnv = ShellEnv( 'IHP SG13G2 Alliance Environment' )
#   shellEnv[ 'MBK_CATA_LIB' ] = shellEnv[ 'MBK_CATA_LIB' ] + ':' + spiceCells.as_posix()
#   shellEnv.export()

#   Iverilog.setStdCellLib( stdCellLibVlog )

#   Klayout.setLypFile( lypFile )
#   DRC.setScript( kdrcScript )
#   ShellEnv.CHECK_TOOLKIT = Where.checkToolkit.as_posix()
#   ShellEnv.PDK_ROOT      = pdkIHPTop.parent.as_posix()
#   ShellEnv.PDK           = 'ihpsg13g2'
#   ShellEnv.KLAYOUT_PATH  = '{}:{}'.format( klayoutHome, klayoutTech )
#   ShellEnv.KLAYOUT_HOME  = '{}'.format( klayoutHome )
#   Filler  .setScript( fillerScript )
#   SealRing.setScript( sealRingScript )

    TasYagle.flags         = TasYagle.Transistor
    TasYagle.SpiceType     = 'hspice'
    TasYagle.SpiceTrModel  = [ (realTechnoDir / 'C4M.Sky130_logic_tt_model.spice').as_posix() ]
#   TasYagle.MBK_CATA_LIB  = '.:' + (ngspiceTech / 'models').as_posix() \
#                          + ':' + (pdkMasterTop).as_posix() \
#                          + ':' + (pdkMasterTop/'libs.ref'/'StdCellLib'/'spice').as_posix()
#   Lvx.MBK_CATA_LIB  = TasYagle.MBK_CATA_LIB
#   x2y.MBK_CATA_LIB  = TasYagle.MBK_CATA_LIB

    TasYagle.MBK_SPI_MODEL = (realTechnoDir / 'spimodel.cfg').as_posix()
    TasYagle.Temperature   = 25.0
    TasYagle.VddSupply     = 1.8 
    TasYagle.VddName       = 'vdd'
    TasYagle.VssName       = 'vss'
    TasYagle.ClockName     = 'm_clock'

