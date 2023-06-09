class GNN:
    def __init__(self, hops, input_sz, output_sz, hidden_sz):
        # example: num_layer 2, hops [3, 3], input_sz 512, output_sz 10, hidden_sz 128
        self.num_layer = len(hops)
        self.fanout_per_hop = hops
        
        self.node_per_hop = [1]
        for layer_i in range(self.num_layer):
            prev_n = self.node_per_hop[-1]
            self.node_per_hop.append(prev_n * self.fanout_per_hop[layer_i])
        
        self.input_sz = input_sz
        self.output_sz = output_sz
        self.hidden_sz = hidden_sz

    def gen_forward(self):
        for layer_i in range(1, self.num_layer+1):
            n_vec = sum(self.node_per_hop[:-layer_i])
            input_sz = self.input_sz if layer_i == 1 else self.hidden_sz
            output_sz = self.output_sz if layer_i == self.num_layer else self.hidden_sz
            print(f"n_input: {n_vec}, input_sz: {input_sz}, output_sz: {output_sz}")

    def gen_backward(self):
        for layer_i in reversed(range(1, self.num_layer+1)):
            n_vec = sum(self.node_per_hop[:self.num_layer+1-layer_i])
            input_sz = self.output_sz if layer_i == self.num_layer else self.hidden_sz
            output_sz = self.input_sz if layer_i == 1 else self.hidden_sz
            print(f"n_vec: {n_vec} outer product vec1: {input_sz}, vec2: {output_sz}")
            if layer_i != 1:
                print(f"n_vec: {n_vec} input sz: {input_sz}, output sz: {output_sz}")

if __name__ == '__main__':
    gnn = GNN([3, 3, 3], 512, 10, 128)
    gnn.gen_forward()
    gnn.gen_backward()
