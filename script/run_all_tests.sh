scripts="$BG_BASE_DIR/script"
pushd $scripts

./run_all_workload.sh
./performance.py

# sensitivity tests
./run_all_sensitivity.sh

./traditional_ssd_test.sh

./storage_efficiency.py
popd