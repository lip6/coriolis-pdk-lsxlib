
import sys
import re
from   coriolis                         import Cfg, CRL, Viewer
from   coriolis.Hurricane               import DataBase, Technology, DbU, Layer, BasicLayer, DiffusionLayer, \
                                               TransistorLayer, RegularLayer, ViaLayer, ContactLayer
from   coriolis.helpers.overlay         import CfgCache
from   coriolis.helpers                 import l, u, n
from   coriolis.helpers.io              import ErrorMessage, vprint
from   coriolis.helpers.technology      import createBL, createVia
from   coriolis.technos.common.colors   import toRGB
from   coriolis.technos.common.patterns import toHexa
from   coriolis.technos.common          import addStyle
from   coriolis.designflow.task         import ShellEnv
from   coriolis.designflow.tasyagle     import TasYagle


def _safeGetTechnology ():
    db = DataBase.getDB()
    if not db:
        raise ErrorMessage( 1, 'techno_symb._safeGetTechnology(): DataBase has not been initialized yet.' )
    tech = db.getTechnology()
    if not tech:
        raise ErrorMessage( 1, 'techno_symb._safeGetTechnology(): Technology has not been initialized yet.' )
    return tech


def _safeGetLayer ( tech, name ):
    layer = tech.getLayer( name )
    if not layer:
        raise ErrorMessage( 1, f'techno_symb._safeGetLayer(): Layer "{name}" does not exists.' )
    return layer


def getMetalNb ( tech ):
    """
    Returns the number of metal layers in technology ``tech``.
    """
    metalNb = 0
    MaterialMetal = BasicLayer.Material(BasicLayer.Material.metal)
    for basicLayer in tech.getBasicLayers():
        if basicLayer.getName().startswith( 'gmetal' ): continue
        if basicLayer.getMaterial() == MaterialMetal:
            metalNb += 1
    return metalNb


def metalMinSize ( i ):
    """
    Returns the minimum size of metal layer ``i`` in symbolic mode.
    """
    if i == 1: return l(1.0)
    return l(2.0)


def metalExtensionCap ( i ):
    """
    Returns extention cap of metal layer ``i`` in symbolic mode.
    """
    if i == 1: return l(0.5)
    return l(1.0)


def setupPureSymb ( metalNb=8 ):
    """
    Initialise the database with a purely symbolic technology. Not an overlay
    on a real one.

    :param metalNb: The number of metallic layers to be createds for this technology.
    """
    from . import libsRefDir
    from . import realTechnoDir
    
    db = DataBase.create()
    CRL.System.get()

    tech = Technology.create( db, 'symbolic' )

    DbU.setPrecision( 2 )
    DbU.setPhysicalsPerGrid( 0.5, DbU.UnitPowerMicro )
    with CfgCache(priority=Cfg.Parameter.Priority.ConfigurationFile) as cfg:
        cfg.gdsDriver.metricDbu = 1e-09
        cfg.gdsDriver.dbuPerUu = 0.001
    DbU.setGridsPerLambda( 2 )
    DbU.setSymbolicSnapGridStep( l(1.0) )
    DbU.setPolygonStep( 1 )
    DbU.setStringMode( DbU.StringModeSymbolic, DbU.UnitPowerMicro )

    createBL( tech, 'nWell'   , BasicLayer.Material.nWell, gds2Layer=1, gds2DataType=0 )
    createBL( tech, 'pWell'   , BasicLayer.Material.nWell, gds2Layer=2, gds2DataType=0 )
    createBL( tech, 'nImplant', BasicLayer.Material.nWell, gds2Layer=3, gds2DataType=0 )
    createBL( tech, 'pImplant', BasicLayer.Material.nWell, gds2Layer=4, gds2DataType=0 )
    createBL( tech, 'active'  , BasicLayer.Material.nWell, gds2Layer=5, gds2DataType=0 )
    createBL( tech, 'poly'    , BasicLayer.Material.nWell, gds2Layer=6, gds2DataType=0 )

    for i in range(1,metalNb+1):
        icut = i-1
        cut   = createBL( tech, f'cut{icut}'  , BasicLayer.Material.cut     , gds2Layer=(i-1)*2+7, gds2DataType=0 )
        metal = createBL( tech, f'metal{i}'   , BasicLayer.Material.metal   , gds2Layer=(i-1)*2+8, gds2DataType=0 )
        block = createBL( tech, f'blockage{i}', BasicLayer.Material.blockage, gds2Layer=(i-1)*2+8, gds2DataType=1 )
        metal.setBlockageLayer( block )

    setupDisplay( metalNb, 1.0 )

    TasYagle.flags         = TasYagle.Transistor
    TasYagle.SpiceType     = 'hspice'
   #TasYagle.SpiceTrModel  = [ 'C4M.Sky130_logic_tt_model.spice' ]
   #TasYagle.MBK_CATA_LIB  = (stdCellDir / 'spice').as_posix() + ':' + ngspiceTechDir.as_posix()
   #Lvx.MBK_CATA_LIB       = TasYagle.MBK_CATA_LIB
   #x2y.MBK_CATA_LIB       = TasYagle.MBK_CATA_LIB
    ShellEnv.MBK_SPI_MODEL = realTechnoDir / 'spimodel.cfg'
    TasYagle.MBK_SPI_MODEL = ShellEnv.MBK_SPI_MODEL
    TasYagle.Temperature   = 25.0
    TasYagle.VddSupply     = 1.8 
    TasYagle.VddName       = 'vdd'
    TasYagle.VssName       = 'vss'
    TasYagle.ClockName     = 'clk'


def setupSymb ():
    """
    Create the symbolic layers on top of the real ones. The real technology
    *must* provides alias names for the *symbolic* basic layers, like "nWell",
    "metal1", "metal2", "cut0", "cut11" and so on.
    """
    tech    = _safeGetTechnology()
    metalNb = getMetalNb( tech )

    nWell    = _safeGetLayer( tech, 'nWell' )
    pWell    = _safeGetLayer( tech, 'pWell' )
    nImplant = _safeGetLayer( tech, 'nImplant' )
    pImplant = _safeGetLayer( tech, 'pImplant' )
    active   = _safeGetLayer( tech, 'active' )
    poly     = _safeGetLayer( tech, 'poly' )

    metals = [ None ]
    METALS = [ None ]
    cuts   = []
    VIAs   = []
    for i in range(1,metalNb+1):
        icut = i-1
        metals.append( _safeGetLayer( tech, f'metal{i}'  ))
        cuts  .append( _safeGetLayer( tech, f'cut{icut}' ))
        
        METALS.append( RegularLayer.create( tech, f'METAL{i}', metals[-1] ))
        tech.setSymbolicLayer( METALS[-1].getName() )
        METALS[-1].setMinimalSize (             metalMinSize(i)      )
        METALS[-1].setExtentionCap( metals[-1], metalExtensionCap(i) )
        if i > 1:
            VIAs.append( ViaLayer.create( tech, f'VIA{icut}{i}', metals[-2], cuts[-1], metals[-1] ))
            tech.setSymbolicLayer( VIAs[-1].getName() )
            VIAs[-1].setMinimalSize   (             l( 1.0) )
            VIAs[-1].setEnclosure     ( metals[-2], l( 0.5), Layer.EnclosureH|Layer.EnclosureV )
            VIAs[-1].setEnclosure     ( metals[-1], l( 0.5), Layer.EnclosureH|Layer.EnclosureV )
            VIAs[-1].setMinimalSpacing(             l( 4.0) )

    # Composite/Symbolic layers.
    NWELL       = RegularLayer   .create( tech, 'NWELL'      , nWell    )
    PWELL       = RegularLayer   .create( tech, 'PWELL'      , pWell    )
    NTIE        = DiffusionLayer .create( tech, 'NTIE'       , nImplant , active, nWell)
    PTIE        = DiffusionLayer .create( tech, 'PTIE'       , pImplant , active, None)
    NDIF        = DiffusionLayer .create( tech, 'NDIF'       , nImplant , active, None )
    PDIF        = DiffusionLayer .create( tech, 'PDIF'       , pImplant , active, None )
    GATE        = DiffusionLayer .create( tech, 'GATE'       , poly     , active, None )
    NTRANS      = TransistorLayer.create( tech, 'NTRANS'     , nImplant , active, poly, None )
    PTRANS      = TransistorLayer.create( tech, 'PTRANS'     , pImplant , active, poly, nWell )
    POLY        = RegularLayer   .create( tech, 'POLY'       , poly     )
    CONT_BODY_N = ContactLayer   .create( tech, 'CONT_BODY_N', metals[1], cuts[0], active, nImplant, pWell )
    CONT_BODY_P = ContactLayer   .create( tech, 'CONT_BODY_P', metals[1], cuts[0], active, pImplant, nWell )
    CONT_DIF_N  = ContactLayer   .create( tech, 'CONT_DIF_N' , metals[1], cuts[0], active, nImplant, pWell )
    CONT_DIF_P  = ContactLayer   .create( tech, 'CONT_DIF_P' , metals[1], cuts[0], active, pImplant, nWell )
    CONT_POLY   = ViaLayer       .create( tech, 'CONT_POLY'  , metals[1], cuts[0], poly,      )
    
    tech.setSymbolicLayer( NWELL      .getName() )
    tech.setSymbolicLayer( PWELL      .getName() )
    tech.setSymbolicLayer( CONT_BODY_N.getName() )
    tech.setSymbolicLayer( CONT_BODY_P.getName() )
    tech.setSymbolicLayer( CONT_DIF_N .getName() )
    tech.setSymbolicLayer( CONT_DIF_P .getName() )
    tech.setSymbolicLayer( CONT_POLY  .getName() )
    tech.setSymbolicLayer( POLY       .getName() )
    
    NWELL.setExtentionCap( nWell, l(0.0) )
    PWELL.setExtentionCap( pWell, l(0.0) )
    
    NTIE.setMinimalSize   (           l(3.0) )
    NTIE.setExtentionCap  ( nWell   , l(1.5) )
    NTIE.setExtentionWidth( nWell   , l(0.5) )
    NTIE.setExtentionCap  ( nImplant, l(1.0) )
    NTIE.setExtentionWidth( nImplant, l(0.5) )
    NTIE.setExtentionCap  ( active  , l(0.5) )
    NTIE.setExtentionWidth( active  , l(0.0) )
    
    PTIE.setMinimalSize   (           l(3.0) )
    PTIE.setExtentionCap  ( nWell   , l(1.5) )
    PTIE.setExtentionWidth( nWell   , l(0.5) )
    PTIE.setExtentionCap  ( nImplant, l(1.0) )
    PTIE.setExtentionWidth( nImplant, l(0.5) )
    PTIE.setExtentionCap  ( active  , l(0.5) )
    PTIE.setExtentionWidth( active  , l(0.0) )
    
    NDIF.setMinimalSize   (           l(3.0) )
    NDIF.setExtentionCap  ( nImplant, l(1.0) )
    NDIF.setExtentionWidth( nImplant, l(0.5) )
    NDIF.setExtentionCap  ( active  , l(0.5) )
    NDIF.setExtentionWidth( active  , l(0.0) )
    
    PDIF.setMinimalSize   (           l(3.0) )
    PDIF.setExtentionCap  ( pImplant, l(1.0) )
    PDIF.setExtentionWidth( pImplant, l(0.5) )
    PDIF.setExtentionCap  ( active  , l(0.5) )
    PDIF.setExtentionWidth( active  , l(0.0) )
    
    GATE.setMinimalSize   (       l(1.0) )
    GATE.setExtentionCap  ( poly, l(1.5) )
    
    NTRANS.setMinimalSize   (           l( 1.0) )
    NTRANS.setExtentionCap  ( nImplant, l(-1.0) )
    NTRANS.setExtentionWidth( nImplant, l( 2.5) )
    NTRANS.setExtentionCap  ( active  , l(-1.5) )
    NTRANS.setExtentionWidth( active  , l( 2.0) )
    
    PTRANS.setMinimalSize   (           l( 1.0) )
    PTRANS.setExtentionCap  ( nWell   , l(-1.0) )
    PTRANS.setExtentionWidth( nWell   , l( 4.5) )
    PTRANS.setExtentionCap  ( pImplant, l(-1.0) )
    PTRANS.setExtentionWidth( pImplant, l( 4.0) )
    PTRANS.setExtentionCap  ( active  , l(-1.5) )
    PTRANS.setExtentionWidth( active  , l( 3.0) )
    
    POLY.setMinimalSize   (       l(1.0) )
    POLY.setExtentionCap  ( poly, l(0.5) )
    
    # Contacts (i.e. Active <--> Metal) (symbolic).
    CONT_BODY_N.setMinimalSize(              l( 1.0) )
    CONT_BODY_N.setEnclosure  ( nWell      , l( 1.5), Layer.EnclosureH|Layer.EnclosureV )
    CONT_BODY_N.setEnclosure  ( nImplant   , l( 1.5), Layer.EnclosureH|Layer.EnclosureV )
    CONT_BODY_N.setEnclosure  ( active     , l( 1.0), Layer.EnclosureH|Layer.EnclosureV )
    CONT_BODY_N.setEnclosure  ( metals[1]  , l( 0.5), Layer.EnclosureH|Layer.EnclosureV )
    
    CONT_BODY_P.setMinimalSize(              l( 1.0) )
    CONT_BODY_P.setEnclosure  ( pImplant   , l( 1.5), Layer.EnclosureH|Layer.EnclosureV )
    CONT_BODY_P.setEnclosure  ( active     , l( 1.0), Layer.EnclosureH|Layer.EnclosureV )
    CONT_BODY_P.setEnclosure  ( metals[1]  , l( 0.5), Layer.EnclosureH|Layer.EnclosureV )
    
    CONT_DIF_N.setMinimalSize(              l( 1.0) )
    CONT_DIF_N.setEnclosure  ( nImplant   , l( 1.0), Layer.EnclosureH|Layer.EnclosureV )
    CONT_DIF_N.setEnclosure  ( active     , l( 0.5), Layer.EnclosureH|Layer.EnclosureV )
    CONT_DIF_N.setEnclosure  ( metals[1]  , l( 0.5), Layer.EnclosureH|Layer.EnclosureV )
    
    CONT_DIF_P.setMinimalSize(              l( 1.0) )
    CONT_DIF_P.setEnclosure  ( pImplant   , l( 1.0), Layer.EnclosureH|Layer.EnclosureV )
    CONT_DIF_P.setEnclosure  ( active     , l( 0.5), Layer.EnclosureH|Layer.EnclosureV )
    CONT_DIF_P.setEnclosure  ( metals[1]  , l( 0.5), Layer.EnclosureH|Layer.EnclosureV )
    
    CONT_POLY.setMinimalSize(            l( 1.0) )
    CONT_POLY.setEnclosure  ( poly     , l( 0.5), Layer.EnclosureH|Layer.EnclosureV )
    CONT_POLY.setEnclosure  ( metals[1], l( 0.5), Layer.EnclosureH|Layer.EnclosureV )


def setupDisplay ( metalNb, scale ):
    styleCoriolisBlack = \
      { 'Name'        : 'Coriolis [black]'
      , 'Description' : 'Coriolis look - black background'
      , 'Darkening'   : Viewer.DisplayStyle.HSVr( 1.0, 3.0, 2.5 )
      , 'Inherit'     : None
      , 'Viewer' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ( 'fallback'       , toRGB('Gray238'    ), 1, '55AA55AA55AA55AA'         , None       )
        , ( 'background'     , toRGB('Gray50'     ), 1, None                       , None       )
        , ( 'foreground'     , toRGB('White'      ), 1, None                       , None       )
        , ( 'rubber'         , toRGB('192,0,192'  ), 2, None                       , 0.02*scale )
        , ( 'phantom'        , toRGB('Seashell4'  ), 1, None                       , None       )
        , ( 'boundaries'     , toRGB('208,199,192'), 1, '0000000000000000'         , 0          )
        , ( 'marker'         , toRGB('80,250,80'  ), 1, None                       , None       )
        , ( 'selectionDraw'  , toRGB('White'      ), 1, None                       , None       )
        , ( 'selectionFill'  , toRGB('White'      ), 1, None                       , None       )
        , ( 'grid'           , toRGB('White'      ), 1, None                       , 2.0*scale  )
        , ( 'spot'           , toRGB('White'      ), 2, None                       , 6.0*scale  )
        , ( 'ghost'          , toRGB('White'      ), 1, None                       , None       )
        , ( 'text.ruler'     , toRGB('White'      ), 1, None                       , 0.0*scale  )
        , ( 'text.instance'  , toRGB('Black'      ), 1, None                       , 4.0*scale  )
        , ( 'text.reference' , toRGB('White'      ), 1, None                       , 20.0*scale )
        , ( 'undef'          , toRGB('Violet'     ), 0, '2244118822441188'         , None       )
        ]                                                                          
      , 'Active Layers' :                                                          
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ( 'nWell'          , toRGB('Tan'        ), 0, '55AA55AA55AA55AA'         , 1.5 *scale )
        , ( 'pWell'          , toRGB('LightYellow'), 0, '55AA55AA55AA55AA'         , 1.50*scale )
        , ( 'nImplant'       , toRGB('LawnGreen'  ), 0, '55AA55AA55AA55AA'         , 1.50*scale )
        , ( 'pImplant'       , toRGB('Yellow'     ), 0, '55AA55AA55AA55AA'         , 1.50*scale )
        , ( 'active'         , toRGB('White'      ), 0, toHexa('antihash1.8')      , 1.50*scale )
        , ( 'poly'           , toRGB('Red'        ), 0, '55AA55AA55AA55AA'         , 1.50*scale )
        ]
      , 'Routing Layers' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ( 'metal1'         , toRGB('Blue'       ), 0, toHexa('poids2.8'         ), 0.80*scale )
        , ( 'metal2'         , toRGB('Aqua'       ), 0, toHexa('light_antihash0.8'), 0.02*scale )
        , ( 'metal3'         , toRGB('LightPink'  ), 0, toHexa('light_antihash1.8'), 0.02*scale )
        , ( 'metal4'         , toRGB('Green'      ), 0, toHexa('light_antihash2.8'), 0.02*scale )
        , ( 'metal5'         , toRGB('Yellow'     ), 0, '1144114411441144'         , 0.02*scale )
        , ( 'metal6'         , toRGB('Violet'     ), 0, toHexa('light_antihash0.8'), 0.02*scale )
        , ( 'metal7'         , toRGB('Violet'     ), 0, toHexa('light_antihash0.8'), 0.02*scale )
        , ( 'metal8'         , toRGB('Violet'     ), 0, toHexa('light_antihash0.8'), 0.02*scale )
        , ( 'metal9'         , toRGB('Violet'     ), 0, toHexa('light_antihash0.8'), 0.02*scale )
        , ( 'metal10'        , toRGB('Violet'     ), 0, toHexa('light_antihash0.8'), 0.02*scale )
        ]
      , 'Cuts (VIA holes)' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('cut0'            , toRGB('0,150,150'  ), 0, None                       , 1.50*scale )
        , ('cut1'            , toRGB('Aqua'       ), 0, None                       , 0.80*scale )
        , ('cut2'            , toRGB('LightPink'  ), 0, None                       , 0.80*scale )
        , ('cut3'            , toRGB('Green'      ), 0, None                       , 0.80*scale )
        , ('cut4'            , toRGB('Yellow'     ), 0, None                       , 0.80*scale )
        , ('cut5'            , toRGB('Violet'     ), 0, None                       , 0.80*scale )
        , ('cut6'            , toRGB('Violet'     ), 0, None                       , 0.80*scale )
        , ('cut7'            , toRGB('Violet'     ), 0, None                       , 0.80*scale )
        , ('cut8'            , toRGB('Violet'     ), 0, None                       , 0.80*scale )
        , ('cut9'            , toRGB('Violet'     ), 0, None                       , 0.80*scale )
        ]
      , 'MIM6' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('metbot_r'        , toRGB('Aqua'       ), 1, toHexa('light_antihash0.8'), 0.80*scale )
        , ('cut6'            , toRGB('LightPink'  ), 1, toHexa('light_antihash1.8'), 0.80*scale )
        , ('metal7'          , toRGB('Green'      ), 1, toHexa('light_antihash2.8'), 0.80*scale )
        ]
      , 'Blockages' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('blockage1'       , toRGB('Blue'       ), 2, '006070381c0e0703'         , 0.80*scale )
        , ('blockage2'       , toRGB('Aqua'       ), 2, '8103060c183060c0'         , 0.80*scale )
        , ('blockage3'       , toRGB('LightPink'  ), 2, toHexa('poids4.8'         ), 0.80*scale )
        , ('blockage4'       , toRGB('Green'      ), 2, toHexa('light_antihash2.8'), 0.80*scale )
        , ('blockage5'       , toRGB('Yellow'     ), 2, '1144114411441144'         , 0.80*scale )
        , ('blockage6'       , toRGB('Violet'     ), 2, toHexa('light_antihash0.8'), 0.80*scale )
        , ('blockage7'       , toRGB('Violet'     ), 2, toHexa('light_antihash0.8'), 0.80*scale )
        , ('blockage8'       , toRGB('Violet'     ), 2, toHexa('light_antihash0.8'), 0.80*scale )
        , ('blockage9'       , toRGB('Violet'     ), 2, toHexa('light_antihash0.8'), 0.80*scale )
        , ('blockage10'      , toRGB('Violet'     ), 2, toHexa('light_antihash0.8'), 0.80*scale )
        ]
      , 'Place & Route' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('gmetalh'         , toRGB('128,255,200'), 1, toHexa('light_antihash0.8'), None       )
        , ('gmetalv'         , toRGB('200,200,255'), 1, toHexa('light_antihash1.8'), None       )
        , ('gcut'            , toRGB('255,255,190'), 1, None                       , None       )
        , ('Anabatic::Edge'  , toRGB('255,255,190'), 4, '0000000000000000'         , 0.02*scale )
        , ('Anabatic::GCell' , toRGB('255,0,0'    ), 4, '0000000000000000'         , 0.02*scale )
        ]
      }

    styleAllianceBlack = \
      { 'Name'        : 'Alliance [black]'
      , 'Description' : 'Alliance look - black background'
      , 'Darkening'   : Viewer.DisplayStyle.HSVr( 1.0, 3.0, 2.5 )
      , 'Inherit'     : None
      , 'Viewer' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('fallback'        , toRGB('Gray238'    ), 1, '55AA55AA55AA55AA'         , None       )
        , ('background'      , toRGB('Gray50'     ), 1, None                       , None       )
        , ('foreground'      , toRGB('White'      ), 1, None                       , None       )
        , ('rubber'          , toRGB('192,0,192'  ), 4, None                       , 0.02*scale )
        , ('phantom'         , toRGB('Seashell4'  ), 1, None                       , None       )
        , ('boundaries'      , toRGB('wheat1'     ), 2, '0000000000000000'         , 0          )
        , ('marker'          , toRGB('205,16,118' ), 2, '0000000000000000'         , None       )
        , ('selectionDraw'   , toRGB('White'      ), 1, None                       , None       )
        , ('selectionFill'   , toRGB('White'      ), 1, None                       , None       )
        , ('grid'            , toRGB('White'      ), 1, None                       , 8.0*scale  )
        , ('spot'            , toRGB('White'      ), 2, None                       , 6.0*scale  )
        , ('ghost'           , toRGB('White'      ), 1, None                       , None       )
        , ('text.ruler'      , toRGB('White'      ), 1, None                       ,   0.0*scale )
        , ('text.instance'   , toRGB('White'      ), 1, None                       , 400.0*scale )
        , ('text.reference'  , toRGB('White'      ), 1, None                       , 200.0*scale )
        , ('undef'           , toRGB('Violet'     ), 0, '2244118822441188'         , None        )
        ]
      , 'Active Layers' :                                                          
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('nWell'           , toRGB('Tan'        ), 1, toHexa('urgo.8')           , 0.00*scale )
        , ('pWell'           , toRGB('LightYellow'), 1, toHexa('urgo.8')           , 0.00*scale )
        , ('nImplant'        , toRGB('LawnGreen'  ), 1, toHexa('antihash0.8')      , 0.00*scale )
        , ('pImplant'        , toRGB('Yellow'     ), 1, toHexa('antihash0.8')      , 0.00*scale )
        , ('active'          , toRGB('White'      ), 1, toHexa('antihash1.8')      , 0.00*scale )
        , ('poly'            , toRGB('Red'        ), 1, toHexa('poids2.8')         , 0.00*scale )
        , ('poly2'           , toRGB('Orange'     ), 1, toHexa('poids2.8')         , 0.00*scale )
        ]
      , 'Routing Layers' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('metal1'          , toRGB('Blue')      ,  1, toHexa('slash.8')          , 0.80*scale )
        , ('metal2'          , toRGB('Aqua')      ,  1, toHexa('poids4.8')         , 0.00*scale )
        , ('metcap'       , toRGB('DarkTurquoise'),  1, toHexa('poids2.8')         , 0.00*scale )
        , ('metal3'          , toRGB('LightPink') ,  1, toHexa('poids4.8')         , 0.00*scale )
        , ('metal4'          , toRGB('Green')     ,  1, toHexa('poids4.8')         , 0.00*scale )
        , ('metal5'          , toRGB('Yellow')    ,  1, toHexa('poids4.8')         , 0.00*scale )
        , ('metal6'          , toRGB('Violet')    ,  1, toHexa('poids4.8')         , 0.00*scale )
        , ('metal7'          , toRGB('Red')       ,  1, toHexa('poids4.8')         , 0.00*scale )
        , ('metal8'          , toRGB('Blue')      ,  1, toHexa('poids4.8')         , 0.00*scale )
        , ('metal9'          , toRGB('Blue')      ,  1, toHexa('poids4.8')         , 0.00*scale )
        , ('metal10'         , toRGB('Blue')      ,  1, toHexa('poids4.8')         , 0.00*scale )
        ]
      , 'Cuts (VIA holes)' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('cut0'            , toRGB('0,150,150') ,  1, None                       ,  0.0*scale )
        , ('cut1'            , toRGB('Aqua')      ,  1, None                       ,  0.0*scale )
        , ('cut2'            , toRGB('LightPink') ,  1, None                       ,  0.0*scale )
        , ('cut3'            , toRGB('Green')     ,  1, None                       ,  0.0*scale )
        , ('cut4'            , toRGB('Yellow')    ,  1, None                       ,  0.0*scale )
        , ('cut5'            , toRGB('Violet')    ,  1, None                       ,  0.0*scale )
        , ('cut6'            , toRGB('Red')       ,  1, None                       ,  0.0*scale )
        , ('cut7'            , toRGB('Blue')      ,  1, None                       ,  0.0*scale )
        , ('cut8'            , toRGB('Blue')      ,  1, None                       ,  0.0*scale )
        , ('cut9'            , toRGB('Blue')      ,  1, None                       ,  0.0*scale )
        ]
      , 'MIM6' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('metbot_r'        , toRGB('Aqua')      ,  1, toHexa('light_antihash0.8'), 0.80*scale )
        , ('metal7'          , toRGB('Green')     ,  1, toHexa('light_antihash2.8'), 0.80*scale )
        ]
      , 'Blockages' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('blockage1'       , toRGB('Blue')      ,  4, toHexa('light_antislash0.8'), 0.80*scale )
        , ('blockage2'       , toRGB('Aqua')      ,  4, toHexa('poids4.8')          , 0.80*scale )
        , ('blockage3'       , toRGB('LightPink') ,  4, toHexa('poids4.8')          , 0.80*scale )
        , ('blockage4'       , toRGB('Green')     ,  4, toHexa('poids4.8')          , 0.80*scale )
        , ('blockage5'       , toRGB('Yellow')    ,  4, toHexa('poids4.8')          , 0.80*scale )
        , ('blockage6'       , toRGB('Violet')    ,  4, toHexa('poids4.8')          , 0.80*scale )
        , ('blockage7'       , toRGB('Red')       ,  4, toHexa('poids4.8')          , 0.80*scale )
        , ('blockage8'       , toRGB('Blue')      ,  4, toHexa('poids4.8')          , 0.80*scale )
        , ('blockage9'       , toRGB('Blue')      ,  4, toHexa('poids4.8')          , 0.80*scale )
        , ('blockage10'      , toRGB('Blue')      ,  4, toHexa('poids4.8')          , 0.80*scale )
        ]
      , 'Place & Route' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('gmetalh'         , toRGB('128,255,200'), 1, toHexa('antislash2.32')    , None       )
        , ('gmetalv'         , toRGB('200,200,255'), 1, toHexa('light_antihash1.8'), None       )
        , ('gcut'            , toRGB('255,255,190'), 1, None                       , None       )
        , ('Anabatic::Edge'  , toRGB('255,255,190'), 4, '0000000000000000'         , 0.02*scale )
        , ('Anabatic::GCell' , toRGB('255,255,190'), 2, '0000000000000000'         , 0.10*scale )
        ]
      }

    styleAllianceWhite = \
      { 'Name'        : 'Alliance [white]'
      , 'Description' : 'Alliance look - white background'
      , 'Darkening'   : Viewer.DisplayStyle.HSVr( 1.0, 3.0, 2.5 )
      , 'Inherit'     : 'Alliance [black]'
      , 'Viewer' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('fallback'        , toRGB('Black')     ,  1, '55AA55AA55AA55AA'         , None       )
        , ('background'      , toRGB('White')     ,  1, None                       , None       )
        , ('foreground'      , toRGB('Black')     ,  1, None                       , None       )
        , ('selectionDraw'   , toRGB('Black')     ,  1, None                       , None       )
        , ('selectionFill'   , toRGB('Black')     ,  1, None                       , None       )
        , ('grid'            , toRGB('Black')     ,  1, None                       , 6.0*scale  )
        , ('spot'            , toRGB('Black')     ,  1, None                       , 6.0*scale  )
        , ('ghost'           , toRGB('Black')     ,  1, None                       , None       )
        , ('text.ruler'      , toRGB('Black')     ,  1, None                       , 0.0 *scale )
        , ('text.instance'   , toRGB('Black')     ,  1, None                       , 4.0 *scale )
        , ('text.reference'  , toRGB('Black')     ,  1, None                       , 20.0*scale )
        , ('undef'           , toRGB('Black')     ,  0, '2244118822441188'         , None       )
        ]
      }

    stylePrinterWhite = \
      { 'Name'        : 'Printer [white]'
      , 'Description' : 'For printers - white background'
      , 'Darkening'   : Viewer.DisplayStyle.HSVr( 1.0, 3.0, 2.5 )
      , 'Inherit'     : None
      , 'Viewer' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('fallback'       , toRGB('Gray238')     ,  1, '55AA55AA55AA55AA'         , None       )
        , ('background'     , toRGB('White')       ,  1, None                       , None       )
        , ('foreground'     , toRGB('Black')       ,  1, None                       , None       )
        , ('rubber'         , toRGB('192,0,192')   ,  4, None                       , 0.02*scale )
        , ('phantom'        , toRGB('Seashell4')   ,  1, None                       , None       )
        , ('boundaries'     , toRGB('Black')       ,  1, '0000000000000000'         , 0          )
        , ('marker'         , toRGB('80,250,80')   ,  1, None                       , None       )
        , ('selectionDraw'  , toRGB('Black')       ,  1, None                       , None       )
        , ('selectionFill'  , toRGB('Black')       ,  1, None                       , None       )
        , ('grid'           , toRGB('Black')       ,  1, None                       , 2.0*scale  )
        , ('spot'           , toRGB('Black')       ,  2, None                       , 6.0*scale  )
        , ('ghost'          , toRGB('Black')       ,  1, None                       , None       )
        , ('text.ruler'     , toRGB('Black')       ,  1, None                       , 0.0 *scale )
        , ('text.instance'  , toRGB('Black')       ,  1, None                       , 4.0 *scale )
        , ('text.reference' , toRGB('Black')       ,  1, None                       , 20.0*scale )
        , ('undef'          , toRGB('Violet')      ,  0, '2244118822441188'         , None       )
        ]
      , 'Active Layers' :                                                          
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('nWell'           , toRGB('Tan')       ,  1, toHexa('urgo.32')          , 0.02*scale )
        , ('pWell'          , toRGB('LightYellow'),  1, toHexa('antipoids2.32')    , 0.02*scale )
        , ('nImplant'        , toRGB('LawnGreen') ,  0, toHexa('diffusion.32')     , 0.02*scale )
        , ('pImplant'        , toRGB('Yellow')    ,  0, toHexa('diffusion.32')     , 0.02*scale )
        , ('active'          , toRGB('White')     ,  0, toHexa('active.32')        , 0.02*scale )
        , ('poly'            , toRGB('Red')       ,  1, toHexa('antipoids2.32')    , 0.02*scale )
        , ('poly2'           , toRGB('Orange')    ,  1, toHexa('antipoids2.32')    , 0.02*scale )
        ]
      , 'Routing Layers' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('metal1'          , toRGB('Blue')      ,  4, toHexa('slash.32'     )    , 0.02*scale )
        , ('metal2'          , toRGB('Aqua')      ,  1, toHexa('antislash2.32')    , 0.02*scale )
        , ('metcap'       , toRGB('DarkTurquoise'),  2, toHexa('poids2.32'    )    , 0.02*scale )
        , ('metal3'          , toRGB('LightPink') ,  1, toHexa('antislash3.32')    , 0.02*scale )
        , ('metal4'          , toRGB('Green')     ,  1, toHexa('antislash4.32')    , 0.02*scale )
        , ('metal5'          , toRGB('Yellow')    ,  1, toHexa('antislash5.32')    , 0.02*scale )
        , ('metal6'          , toRGB('Violet')    ,  1, toHexa('antislash2.32')    , 0.02*scale )
        , ('metal7'          , toRGB('Violet')    ,  1, toHexa('antislash2.32')    , 0.02*scale )
        , ('metal8'          , toRGB('Violet')    ,  1, toHexa('antislash2.32')    , 0.02*scale )
        , ('metal9'          , toRGB('Violet')    ,  1, toHexa('antislash2.32')    , 0.02*scale )
        , ('metal10'         , toRGB('Violet')    ,  1, toHexa('antislash2.32')    , 0.02*scale )
        ]
      , 'Cuts (VIA holes)' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('cut0'            , toRGB('Blue')      ,  2, toHexa('poids2.8'    )     , 0.02*scale )
        , ('cut1'            , toRGB('Aqua')      ,  2, toHexa('antipoids2.8')     , 0.02*scale )
        , ('cut2'            , toRGB('LightPink') ,  2, toHexa('poids2.8'    )     , 0.02*scale )
        , ('cut3'            , toRGB('Green')     ,  2, toHexa('antipoids2.8')     , 0.02*scale )
        , ('cut4'            , toRGB('Yellow')    ,  2, toHexa('poids2.8'    )     , 0.02*scale )
        , ('cut5'            , toRGB('Violet')    ,  2, toHexa('antipoids2.8')     , 0.02*scale )
        , ('cut6'            , toRGB('Violet')    ,  2, toHexa('antipoids2.8')     , 0.02*scale )
        , ('cut7'            , toRGB('Violet')    ,  2, toHexa('antipoids2.8')     , 0.02*scale )
        , ('cut8'            , toRGB('Violet')    ,  2, toHexa('antipoids2.8')     , 0.02*scale )
        , ('cut9'            , toRGB('Violet')    ,  2, toHexa('antipoids2.8')     , 0.02*scale )
        ]
      , 'MIM6' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('metbot_r'        , toRGB('Aqua')      ,  0, toHexa('light_antihash0.8'), 0.80*scale )
        , ('cut6'            , toRGB('LightPink') ,  0, toHexa('light_antihash1.8'), 0.80*scale )
        , ('metal7'          , toRGB('Green')     ,  0, toHexa('light_antihash2.8'), 0.80*scale )
        ]
      , 'Blockages' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('blockage1'       , toRGB('Blue')      ,  2, '006070381c0e0703'         , 0.80*scale )
        , ('blockage2'       , toRGB('Aqua')      ,  2, '8103060c183060c0'         , 0.80*scale )
        , ('blockage3'       , toRGB('LightPink') ,  2, toHexa('poids4.8'         ), 0.80*scale )
        , ('blockage4'       , toRGB('Green')     ,  2, toHexa('light_antihash2.8'), 0.80*scale )
        , ('blockage5'       , toRGB('Yellow')    ,  2, '1144114411441144'         , 0.80*scale )
        , ('blockage6'       , toRGB('Violet')    ,  2, toHexa('light_antihash0.8'), 0.80*scale )
        , ('blockage7'       , toRGB('Violet')    ,  2, toHexa('light_antihash0.8'), 0.80*scale )
        , ('blockage8'       , toRGB('Violet')    ,  2, toHexa('light_antihash0.8'), 0.80*scale )
        , ('blockage9'       , toRGB('Violet')    ,  2, toHexa('light_antihash0.8'), 0.80*scale )
        , ('blockage10'      , toRGB('Violet')    ,  2, toHexa('light_antihash0.8'), 0.80*scale )
        ]
      , 'Place & Route' :
        # | Name             | Color              | B | Pattern                    | Threshold  |
        [ ('gmetalh'         , toRGB('128,255,200'), 1, toHexa('light_antihash0.8'), None       )
        , ('gmetalv'         , toRGB('200,200,255'), 1, toHexa('light_antihash1.8'), None       )
        , ('gcut'            , toRGB('255,255,190'), 1, None                       , None       )
        , ('Anabatic::Edge'  , toRGB('255,255,190'), 2, '0000000000000000'         , None       )
        , ('Anabatic::GCell' , toRGB('Black')      , 2, '0000000000000000'         , 0.80*scale )
        ]
      }

    addStyle( styleCoriolisBlack, metalNb )
    addStyle( styleAllianceBlack, metalNb )
    addStyle( styleAllianceWhite, metalNb )
    addStyle( stylePrinterWhite , metalNb )
    Viewer.Graphics.setStyle( styleAllianceBlack['Name'] )
