set -e
ulimit -c 0

uniqid=`git rev-parse HEAD`
xml=instructions.xml
python=./env/bin/python

if [ ! -e $xml ]
then
        echo "Please run this script from the same directory as $xml is in."
        exit 1
fi

if [ ! -x $python ]
then
        echo "Could not find python interpreter at $python. Please see README.md to set it up."
        exit 1
fi


if [ "$#" -ne 1 ]
then    echo "Usage: $0 <uarch>"
        echo "<uarch> should be specified using the three-letter convention (e.g. SKL)."
        echo "The arch should be an arch that instructions.xml knows about, i.e.: "
        xmlstarlet sel -t -m "//architecture" -v "@name" -n <$xml | sort | uniq
        uarch=`$python uarch.py`
        echo -n "Detected uarch $uarch. Continue with uarch $uarch? (y/n) "
        read yn
        if [ $yn != y ]
        then exit 1
        fi
else
    uarch="$1"
fi

echo "Run full or quick test?"
echo "Full test:  ALL instructions in NxN combinations, and many iterations"
echo "            for high quality signal. This can take a long time (few hours)."
echo "Quick test: 500 instructions in NxN combinations, and fewer iterations"
echo "            than in Full mode. This should take a coffee amount of time."
echo -n "Full or Quick? (f/Q) "
read fullquick
if [ "$fullquick" = f -o "$fullquick" = F ]
then    modename=full
        iterations=2000
        instrs_cutoff=0
elif [ "$fullquick" = q -o "$fullquick" = Q -o "$fullquick" = "" ]
then    modename=quick
        iterations=200
        instrs_cutoff=500
else
        echo "Do not understand response"
        exit 1
fi

echo "Mode: $modename Measurement iterations: $iterations Try how many instructions: $instrs_cutoff"

asmfile=s/out-$uarch.S
exe=bin/test-$uarch-$uniqid

echo uarch: $uarch asmfile: $asmfile executable: $exe
if [ ! -s $asmfile ]
then	echo "Generating assembly file $asmfile"
	$python xmlToAssembler.py $uarch >s/out-$uarch.S
	echo "Generating assembly file done"
else	echo "Using existing $asmfile"
fi

echo "Compiling with C test program"
gcc -Ic/ -o$exe c/instrout-test.c s/out-$uarch.S -no-pie -pthread
echo "Assigning the CAP_SYS_NICE capability to the test program, which needs sudo"
sudo setcap 'cap_sys_nice=eip' $exe
echo "Compiling with C test program done"

echo "Executing test program in all combinations, doing $iterations iterations"
echo "If anything goes wrong here, re-run the command from the shellscript without the progressbar argument to see verbose output."
set -x
$python testall.py ./$exe testall $uarch $iterations $instrs_cutoff  progressbar
set +x
echo "Executing test program in all combinations done"

echo "Executing in aggregate mode"
echo "If anything goes wrong here, re-run the command from the shellscript without the progressbar argument to see verbose output."
set -x
$python testall.py aggregate progressbar
set +x
echo "Executing aggregate done"

echo "Executing data plot, which will plot data for all archs in state/"
set -x
$python numpyplot.py
set +x
echo "Done"
