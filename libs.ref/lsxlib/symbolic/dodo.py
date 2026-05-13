
DOIT_CONFIG = { 'verbosity' : 2 }

import sys
from   pathlib import Path
pdkTop = (Path().cwd() / '..' / '..' / '..' / 'libs.tech' / 'coriolis').resolve()
sys.path.append( pdkTop.as_posix() )

import os
from   doit   import get_var
from   lsxlib import setup, USE_REAL_RDS

#techno        = 'sky130'
techno        = 'ihpsg13g2'
#techno        = 'symbolic'
useSymb       = get_var( 'use-symb-rds'  , False )
updateDistrib = get_var( 'update-distrib', False )

setupFlags = USE_REAL_RDS
if useSymb: setupFlags &= ~USE_REAL_RDS 

setup( techno, setupFlags )

from coriolis                     import CRL
from coriolis.designflow.task     import ShellEnv, Tasks
from coriolis.designflow.klayout  import Klayout
from coriolis.designflow.lvx      import Lvx
from coriolis.designflow.x2y      import x2y
from coriolis.designflow.graal    import Graal
from coriolis.designflow.dreal    import Dreal
from coriolis.designflow.druc     import Druc
from coriolis.designflow.cougar   import Cougar
from coriolis.designflow.vasy     import Vasy
from coriolis.designflow.proof    import Proof
from coriolis.designflow.s2r      import S2R
from coriolis.designflow.tasyagle import TasYagle, STA, XTas, ExtractCell, Liberty
from coriolis.designflow.copy     import Copy
from coriolis.designflow.alias    import Alias
from coriolis.designflow.group    import Group
from coriolis.designflow.pnr      import PnR
from coriolis.designflow.clean    import Clean

if techno == 'ihpsg13g2':
    from pdks.ihpsg13g2_c4m.designflow.drc import DRC 
else:
    from coriolis.designflow.klayout  import DRC


cougarFlags   = Cougar.Transistor|Cougar.GroundCap|Cougar.WireRC
libertyFlags  = 0
checkLibRules = []
cellVhdFiles  = []
if updateDistrib:
    cougarFlags  |= Cougar.KeepSpice
    libertyFlags |= TasYagle.KeepLiberty


def lookForCells ():
    ApView  = 0x0001
    VbeView = 0x0002

    stdCellViews = {}
    for fileName in Path().cwd().iterdir():
        if fileName.stem == 'tie_x0':    continue
        if fileName.stem == 'rowend_x0': continue
        if fileName.suffix == '.ap':
            if fileName.stem in stdCellViews: stdCellViews[ fileName.stem ] |= ApView
            else:                             stdCellViews[ fileName.stem ]  = ApView
        if fileName.suffix == '.vbe':
            if fileName.stem in stdCellViews: stdCellViews[ fileName.stem ] |= VbeView
            else:                             stdCellViews[ fileName.stem ]  = VbeView

    stdCells = []
    for cellName, views in stdCellViews.items():
        if (views & ApView) and (views & VbeView):
            stdCells.append( cellName )
    return stdCells


def checkCell ( cellName ):
    """
    Creates the rules needed to check one individual cell and adds the final
    ones ('druc.cellName' & 'proof.cellName') to the library group of rules.

    The chain of rules that are executeds are: ::

        1. druc
        2. cougar --> yagle --> vasy --> proof
    """
    global techno
    global checkLibRules
    global cellsVhdFiles

    ruleDruc    = Druc       .mkRule( f'druc.{cellName}'  , f'{cellName}.spi' )
    ruleCougar  = Cougar     .mkRule( f'cougar.{cellName}', f'{cellName}.spi'
                                                          , f'{cellName}.ap'
                                                          , flags=cougarFlags )
    ruleExtract = ExtractCell.mkRule( f'yagle.{cellName}' , f'{cellName}.spi' )
    ruleVasy    = Vasy       .mkRule( f'vasy.{cellName}'  , f'{cellName}_ext.vbe'
                                                          , f'{cellName}.vhd'
                                                          , Vasy.VbeCompliant )
    ruleProof   = Proof      .mkRule( f'proof.{cellName}' , [ f'{cellName}.vbe'
                                                            , f'{cellName}_ext.vbe' ]
                                                          , Proof.DisplayErrors )
    if techno != 'symbolic':
       ruleS2R    = S2R         .mkRule( f's2r.{cellName}'   , f'{cellName}.gds'
                                                             , f'{cellName}.ap' )
       ruleDRC    = DRC         .mkRule( f'drc.{cellName}'   , f'{cellName}.gds' )
    checkLibRules += [ ruleDruc, ruleProof ]
    cellVhdFiles.append( f'{cellName}.vhd' )

    if updateDistrib:
        ruleCopy = Copy.mkRule( f'copy.{cellName}', f'../{techno}/{cellName}.spi'
                                                  ,             f'{cellName}.spi' )
        checkLibRules.append( ruleCopy )


stdCells = lookForCells()
#stdCells = [ 'inv_x1', 'a2_x2' ]
print( '  o  Standard cells found in the current directory:' )
for cellName in stdCells:
    print( f'     - "{cellName}"' )
    checkCell( cellName )


ruleLiberty = Liberty.mkRule( 'liberty', 'lsxlib.lib', cellVhdFiles, libertyFlags )
checkLibRules.append( ruleLiberty )
if updateDistrib:
    ruleCopy = Copy.mkRule( 'copy.liberty', f'../{techno}/lsxlib.lib', f'lsxlib.lib' )
    checkLibRules.append( ruleCopy )

ruleGraal = Graal.mkRule( 'graal', flags=Graal.Config )
ruleDreal = Dreal.mkRule( 'dreal', flags=Dreal.Config )
ruleCgt   = PnR  .mkRule( 'cgt' )
ruleClean = Clean.mkRule( [ 'cgt.log' ] )
ruleGroup = Group.mkRule( 'check-lib', checkLibRules )
