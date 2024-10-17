import pandas as pd


class GNNTopology:
    def __init__(self, batch, hops, input_dim, output_dim, hidden_dim):
        # example: num_layer 2, hops [3, 3], input_dim 125, output_dim 10, hidden_dim 128
        self.batch = batch
        self.num_layer = len(hops)
        self.fanout_per_hop = hops
        
        self.node_per_hop = [1]
        for layer_i in range(self.num_layer):
            prev_n = self.node_per_hop[-1]
            self.node_per_hop.append(prev_n * self.fanout_per_hop[layer_i])
        
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.hidden_dim = hidden_dim

        self.topo = None

    def gen_forward(self):
        for layer_i in range(1, self.num_layer+1):
            n_vec = sum(self.node_per_hop[:-layer_i])
            input_dim = self.input_dim if layer_i == 1 else self.hidden_dim
            output_dim = self.output_dim if layer_i == self.num_layer else self.hidden_dim
            # print(f"n_input: {n_vec}, input_dim: {input_dim}, output_dim: {output_dim}")
            row = {'Layer': f'Forward_Activation_{layer_i}', 'M': self.batch * n_vec, 'N': output_dim, 'K': input_dim}
            self.topo.loc[len(self.topo)] = row

    def gen_backward(self):
        for layer_i in reversed(range(1, self.num_layer+1)):
            n_vec = sum(self.node_per_hop[:self.num_layer+1-layer_i])
            input_dim = self.output_dim if layer_i == self.num_layer else self.hidden_dim
            output_dim = self.input_dim if layer_i == 1 else self.hidden_dim
            # print(f"n_vec: {n_vec} outer product vec1: {input_dim}, vec2: {output_dim}")
            row = {'Layer': f'Backward_Weight_{layer_i}', 'M': input_dim, 'N': output_dim, 'K': self.batch * n_vec}
            self.topo.loc[len(self.topo)] = row

            if layer_i != 1:
                # print(f"n_vec: {n_vec} input dim: {input_dim}, output dim: {output_dim}")
                row = {'Layer': f'Backward_Activation_{layer_i}', 'M': n_vec * self.batch, 'N': output_dim, 'K': input_dim}
                self.topo.loc[len(self.topo)] = row

    def gen_topo(self):
        self.topo = pd.DataFrame(columns=['Layer', 'M', 'N', 'K'])
        self.gen_forward()
        self.gen_backward()
        return self.topo

    def cal_total_mac(self):
        if self.topo is None:
            self.gen_topo()
        total_mac = 0
        for topo_i in range(len(self.topo)):
            row = self.topo.iloc[topo_i]
            total_mac += row['M'] * row['N'] * row['K']
        return total_mac

    def dump_csv(self, path):
        if self.topo is None:
            self.gen_topo()
        self.topo.to_csv(path, index=False)

if __name__ == '__main__':
    gnn = GNNTopology(128, [3, 3, 3], 128, 10, 128)
    df = gnn.gen_topo()
    print(df)
    print("total macs ", gnn.cal_total_mac())
    
    gnn.dump_csv('gnn_topo.csv')
    
    import os
    from scale_sim import scalesim
    s = scalesim(save_disk_space=True, verbose=False,
                 config=os.environ['BG_BASE_DIR'] + '/configs/accelerator/isc_tpu.cfg',
                 topology='gnn_topo.csv',
                 input_type_gemm=True
                 )
    s.run_scale(top_path=os.environ['BG_BASE_DIR'] + '/generated')
    total_cyles = s.get_total_cycles()
    print("total cycles ", total_cyles)