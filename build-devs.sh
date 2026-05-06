#!/bin/sh

 getString () { string=`echo $1 | cut -d '=' -f 2-`; echo $string; }


 rootDir="`cd ../..; pwd`"
 while [ $# -gt 0 ]; do
   case $1 in
     --root-dir) rootDir="`getString $1`"
                 echo "Forcing root directory to \"${rootDir}\".";;
   esac
   shift
 done

 echo "Using rootDir=\"${rootDir}\"."

   buildDir="${rootDir}/release/build-lsxlib"
 installDir="${rootDir}/release/install"
 rm -rf ${buildDir}
 rm -rf ${installDir}/lib64/python3.9/site-packages/pdks/lsxlib
 meson setup --prefix ${installDir} ${buildDir}
 meson install -C ${buildDir}
