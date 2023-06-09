from dram import Buffer
import numpy as np

buf = Buffer(10, 100)

def skew_matrix(input_matrix_np):
    rows = input_matrix_np.shape[0]
    cols = input_matrix_np.shape[1]

    out_matrix_np = np.zeros((1,1))
    for c in range(cols):
        if c == 0:
            down_padding = -1 * np.ones((cols-1, 1))
            mat_col = input_matrix_np[:,c].reshape((rows,1))
            out_matrix_np = np.concatenate((mat_col, down_padding), axis=0)

        else:
            if c == cols -1:
                up_padding = -1 * np.ones((cols-1, 1))
                mat_col = input_matrix_np[:, c].reshape((rows, 1))

                this_col = np.concatenate((up_padding, mat_col), axis=0)
                out_matrix_np = np.concatenate((out_matrix_np, this_col), axis=1)

            else:
                up_padding = -1 * np.ones((c, 1))
                mat_col = input_matrix_np[:, c].reshape((rows, 1))
                down_padding = -1 * np.ones((cols - c -1, 1))

                this_col = np.concatenate((up_padding, mat_col, down_padding), axis=0)
                out_matrix_np = np.concatenate((out_matrix_np, this_col), axis=1)

    return out_matrix_np

mat = np.array([[1,4,7], [2,5,8], [3,6,9]])
skew = skew_matrix(mat)
print(skew)