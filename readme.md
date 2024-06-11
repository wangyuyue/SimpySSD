## <font color="#FFD43B">Sim</font><font color="#306998">py</font><font color="#646464">SSD</font>: A Simple SSD Simulator in Python

### Install
```bash
git clone https://github.com/wangyuyue/SimpySSD.git
cd SimpySSD
pip3 install -r requirements.txt
```
### Example usage
```bash
workload=amazon
python3 src/main.py --workload "$workload"
```

### Citation
If you find this project interesting and useful, please consider citing our publication:
```bibtex
@inproceedings{wang2024beacongnn,
  title={BeaconGNN: Large-Scale GNN Acceleration with Out-of-Order Streaming In-Storage Computing},
  author={Wang, Yuyue and Pan, Xiurui and An, Yuda and Zhang, Jie and Reinman, Glenn},
  booktitle={2024 IEEE International Symposium on High-Performance Computer Architecture (HPCA)},
  pages={330--344},
  year={2024},
  organization={IEEE}
}
```

### Acknowledgment
SimpySSD is developed for BeaconGNN (HPCA 2024). It is inspired by the famous C++ simulator [MQSim](https://github.com/CMU-SAFARI/MQSim). We choose Python for faster development and more flexible design space exploration.