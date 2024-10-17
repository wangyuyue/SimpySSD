if [ "$(basename "$(pwd)")" != "SimpySSD" ]; then
    echo "You are not in the SimpySSD base directory."
    return 1
fi

git submodule update --init --recursive
pushd scalesim; sudo python3 setup.py install; popd
cp scalesim/scalesim/scale_sim.py src/

export BG_BASE_DIR=$(pwd)
export PYG_DATA_DIR="$BG_BASE_DIR/pg"
export BG_TEST_DIR="$BG_BASE_DIR/test"
export BG_MAIN="$BG_BASE_DIR/src/main.py"