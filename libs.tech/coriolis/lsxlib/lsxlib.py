
import sys
from   pathlib                  import Path
from   coriolis                 import Cfg, CRL
from   coriolis.Hurricane       import Technology, DataBase, DbU, Library, Layer,         \
                                       BasicLayer, Cell, Net, Horizontal, Vertical,       \
                                       Rectilinear, Box, Point, Instance, Transformation, \
                                       NetExternalComponents, Pad
import coriolis.Viewer
from   coriolis.CRL             import AllianceFramework, Gds, LefImport, CellGauge,  \
                                       RoutingGauge, RoutingLayerGauge
from   coriolis.helpers         import l, u, n, overlay, io, ndaTopDir
from   coriolis.helpers.overlay import CfgCache, UpdateSession
from   coriolis.Anabatic        import StyleFlags
from   .                        import libsRefDir


__all__ = [ "setup" ]


def _routing ():
    """
    Overwrite the native routing parameters to fit with the LSxLib symbolic
    library. This only a partial one:

    ========================  ========================
    Component                 State
    ========================  ========================
    Routing gauge             kept (real)
    Cell gauge                overwritten (symbolic)
    Configuration parameters  partially overwritten
    ========================  ========================
    """
    af = AllianceFramework.get()
    io.vprint( 2, f'     Setting up P&R configuration.' )

    cg = CellGauge.create( 'LSxLib'
                         , 'MET1'     # pin layer name.
                         , l(  5.0 )  # pitch.
                         , l( 50.0 )  # cell slice height.
                         , l(  5.0 )  # cell slice step.
                         )
    af.addCellGauge( cg )
    af.setCellGauge( 'LSxLib' )

    with CfgCache(priority=Cfg.Parameter.Priority.ConfigurationFile) as cfg:
        env = af.getEnvironment()
        env.setRegister( '^sff.*' )
        # Place & Route setup
        cfg.crlcore.groundName  = 'vss'
        cfg.crlcore.powerName   = 'vdd'
        cfg.etesian.diodeName   = None
        cfg.etesian.antennaInsertThreshold = 0
        cfg.etesian.antennaMaxWL = 0
        cfg.etesian.spares.buffer = 'buf_x4'
        cfg.etesian.tieName = 'tie_x0'
        cfg.etesian.feedNames = 'tie_x0'
        cfg.etesian.defaultFeed = 'tie_x0'
        cfg.etesian.cell.zero = 'zero_x0'
        cfg.etesian.cell.one = 'one_x0'
        cfg.anabatic.cellGauge = 'LSxLib'
        cfg.anabatic.gcellAspectRatio = 1.0 
        cfg.anabatic.smallNetWidth  = l(50.0*0.33)
        cfg.anabatic.smallNetHeight = l(50.0*1.30)
        cfg.anabatic.globalLengthThreshold = 30*l(50.0)
        cfg.anabatic.hsmallThreshold = 3
        cfg.anabatic.vsmallThreshold = 3
        cfg.anabatic.vlargeThreshold = 6
        cfg.anabatic.saturateRatio = 0.90
        cfg.anabatic.saturateRp = 10
        cfg.anabatic.netBuilderStyle = 'HV,3RL+'
        cfg.anabatic.routingStyle = StyleFlags.HV|StyleFlags.M1Offgrid|StyleFlags.VSmallAsOffgrid
        cfg.katana.hTracksReservedMin = 5
        cfg.katana.hTracksReservedLocal = 7
        cfg.katana.hTracksReservedLocal = [0, 18]
        cfg.katana.vTracksReservedMin = 7
        cfg.katana.vTracksReservedLocal = 10
        cfg.katana.vTracksReservedLocal = [0, 28]
        cfg.katana.termSatReservedLocal = 8
        cfg.katana.termSatThreshold = 9
        cfg.katana.eventsLimit = 4000002
        cfg.katana.ripupCost = 3
        cfg.katana.ripupCost = [0, None]
        # Plugins setup
        cfg.clockTree.minimumSide = l(50.0) * 6
        cfg.clockTree.buffer = 'buf_x4'
        cfg.block.spareSide = 10
        cfg.block.upperEastWestPins = False
        cfg.spares.buffer = 'buf_x4'
        cfg.spares.hfnsBuffer = 'buf_x4'
        cfg.spares.maxSinks = 20


def _loadLSxLib ():
    """
    Load the symbolic LSxLib standard cell library.
    """
    configFile = Path(__file__).resolve()
    io.vprint( 1, '  o  Setup LSxLib symbolic library.' )
    io.vprint( 2, '     (__file__="{}")'.format( configFile.as_posix() ))

    cellsDir = libsRefDir / 'lsxlib' / 'symbolic'
    af       = AllianceFramework.get()
    env      = af.getEnvironment()
    env.addSYSTEM_LIBRARY( library=cellsDir.as_posix(), mode=CRL.Environment.Append )


def setup ():
    _routing()
    _loadLSxLib()
