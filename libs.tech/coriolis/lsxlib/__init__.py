
from pathlib import Path
from coriolis                     import CRL, Cfg, Viewer
from coriolis.helpers             import overlay, l, u, n
from coriolis.helpers.io          import ErrorMessage, vprint
from coriolis.designflow.technos  import Where
from coriolis.designflow.task     import ShellEnv
from coriolis.designflow.yosys    import Yosys
from coriolis.designflow.iverilog import Iverilog
from coriolis.designflow.klayout  import Klayout
from coriolis.designflow.lvx      import Lvx
from coriolis.designflow.x2y      import x2y
from coriolis.designflow.tasyagle import TasYagle


__all__ = [ 'setup', 'USE_REAL_RDS' ]


USE_REAL_RDS = 0x0001


isPdkInstalled = False
realTechnoDir  = None
libsRefDir     = None


def _setupSymbolic ( flags ):
    global isPdkInstalled
    global realTechnoDir
    global libsRefDir

    from .techno_symb import setupPureSymb, setupSymb

    setupPureSymb()
    setupSymb()

    cellsDir     = libsRefDir   / 'lsxlib'
    cellsTechDir = cellsDir     / 'symbolic'
    liberty      = cellsTechDir / 'lsxlib-symb.lib'
    if isPdkInstalled: Yosys.setLiberty( liberty )


def _setupSky130_c4m ( flags ):
    global isPdkInstalled
    global realTechnoDir
    global libsRefDir

    from pdks.sky130_c4m import setup as setupReal

    setupReal()

    cellsDir     = libsRefDir   / 'lsxlib'
    cellsTechDir = cellsDir     / 'sky130'
    liberty      = cellsTechDir / 'lsxlib.lib'

    shellEnv = ShellEnv( 'SkyWater 130A Alliance Environment' )
    shellEnv[ 'MBK_CATA_LIB' ] = shellEnv[ 'MBK_CATA_LIB' ] + ':' + cellsDir.as_posix()
    shellEnv.export()
    if isPdkInstalled: Yosys.setLiberty( liberty )

    if len(TasYagle.MBK_CATA_LIB):
        TasYagle.MBK_CATA_LIB = TasYagle.MBK_CATA_LIB + ':' + (cellsTechDir).as_posix()
    else:
        TasYagle.MBK_CATA_LIB = '.:' + (cellsTechDir).as_posix()


def _setupIhpsg13g2_c4m ( flags ):
    global isPdkInstalled
    global realTechnoDir
    global libsRefDir

    from pdks.ihpsg13g2_c4m import setup as setupReal
    from .techno_symb       import setupSymb

    setupReal()
    setupSymb()

    cellsDir     = libsRefDir   / 'lsxlib'
    cellsTechDir = cellsDir     / 'ihpsg13g2'
    liberty      = cellsTechDir / 'lsxlib.lib'

    shellEnv = ShellEnv( 'SkyWater 130A Alliance Environment' )
    shellEnv[ 'MBK_CATA_LIB' ] = shellEnv[ 'MBK_CATA_LIB' ] + ':' + cellsDir.as_posix()
    shellEnv.export()
    if isPdkInstalled: Yosys.setLiberty( liberty )

    if len(TasYagle.MBK_CATA_LIB):
        TasYagle.MBK_CATA_LIB = TasYagle.MBK_CATA_LIB + ':' + (cellsTechDir).as_posix()
    else:
        TasYagle.MBK_CATA_LIB = '.:' + (cellsTechDir).as_posix()


def setup ( techno=None, flags=0 ):
    global isPdkInstalled
    global realTechnoDir
    global libsRefDir

    if techno is None:
        raise ErrorMessage( 1, 'lsxlib.setup(): <techno> argument has not been set.' )
    
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

    if   techno == 'symbolic':  pass
    elif techno == 'ihpsg13g2': pass
    elif techno == 'sky130':    pass
    else:
        raise ErrorMessage( 1, f'lsxlib.setup(): techno="{techno}" is not supported.' )
    if isPdkInstalled:
        libsRefDir    = Path( __file__ ).parent / 'libs.ref'
        realTechnoDir = Path( __file__ ).parent / 'libs.tech' / 'coriolis' / techno
    else:
        libsRefDir    = Path( __file__ ).parents[3] / 'libs.ref'
        realTechnoDir = Path( __file__ ).parents[0] / techno
    if not realTechnoDir.is_dir():
        raise ErrorMessage( 1, [ f'lsxlib.setup(): techno="{techno}" directory is missing.'
                               , f'({realTechnoDir})' ] )

    Where()

    if techno == 'symbolic':  _setupSymbolic     ( flags )
    if techno == 'sky130':    _setupSky130_c4m   ( flags )
    if techno == 'ihpsg13g2': _setupIhpsg13g2_c4m( flags )

    ShellEnv.RDS_TECHNO_NAME = (realTechnoDir / 'symbolic.rds').as_posix()
    if techno != 'symbolic' and flags & USE_REAL_RDS:
        ShellEnv.RDS_TECHNO_NAME = (realTechnoDir / f'{techno}_lsx.rds').as_posix()
    ShellEnv.GRAAL_TECHNO_NAME = (realTechnoDir / 'symbolic.graal').as_posix()
   #ShellEnv.DREAL_TECHNO_NAME = (realTechnoDir / 'symbolic.dreal').as_posix()
   #ShellEnv.MBK_SPI_MODEL     = (realTechnoDir / 'spimodel.cfg'  ).as_posix()

    cellsDir = libsRefDir / 'lsxlib' / 'symbolic'
    af       = CRL.AllianceFramework.get()
    env      = af.getEnvironment()
    env.addSYSTEM_LIBRARY( library=cellsDir.as_posix(), mode=CRL.Environment.Prepend )

