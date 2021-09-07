from numpy import *
import matplotlib.pyplot as plt
from PyCoupling.mom_2d_capacitance import *
import argparse
 
def test_kernel_flat(mode="single-gp"):
    N = 101
    size = 3
    Y, X = meshgrid(linspace(-size, size, N), linspace(-size, size, N))
    
    Z = zeros([N-1,N-1])
    for ix in range(N-1):
        for iy in range(N-1):
            x = X[ix,iy]
            y = Y[ix,iy]
            
            if mode=="single":
                Z[ix,iy] = kernel_flat([x,y], [1,0], [0, 1], 1)
            elif mode=="square":
                Z[ix,iy] =  kernel_flat([x,y], [0.5,0],   [0, 1], 1)
                Z[ix,iy] += kernel_flat([x,y], [-0.5, 0], [0, 1], 1)
                Z[ix,iy] += kernel_flat([x,y], [0, 0.5],  [1, 0], 1)
                Z[ix,iy] += kernel_flat([x,y], [0, -0.5], [1, 0], 1)
            elif mode=="single-gp":
                Z[ix,iy] =  kernel_flat_gp([x,y], [0,1],   [1, 0], 1)
            else: # mode=="square-gp":
                Z[ix,iy] =  kernel_flat_gp([x,y], [0.5,1],   [0, 1], 1)
                Z[ix,iy] += kernel_flat_gp([x,y], [-0.5, 1], [0, 1], 1)
                Z[ix,iy] += kernel_flat_gp([x,y], [0, 1.5],  [1, 0], 1)
                Z[ix,iy] += kernel_flat_gp([x,y], [0, 0.5], [1, 0], 1)
                
    fig, ax = plt.subplots()
    
    z_min, z_max = -abs(Z).max(), abs(Z).max()
    
    c = ax.pcolormesh(X, Y, Z, cmap='RdBu', vmin=z_min, vmax=z_max)
    ax.set_title('Flat Kernel Test: ' + mode)
    # set the limits of the plot to the limits of the data
    ax.axis([X.min(), X.max(), Y.min(), Y.max()])
    fig.colorbar(c, ax=ax)

    plt.show()

if __name__ == "__main__":
    #
    parser = argparse.ArgumentParser("mom_2d_capacitance.py - Test Bench")
    parser.add_argument("--cable", help="Cable selection", type=str, default="romex_setup_three")
    parser.add_argument("--plot", help="Plot solution: True/False", type=bool, default=False)
    args = parser.parse_args()

    # Test bench
    struc = generate_struct_obj("Cables/{}.json".format(args.cable))
    print(struc["conductors"])
    
    #print("Mode: " + args.mode)
    #test_kernel_flat(mode=args.mode)
    
    Y, Y_inv, seg_struc = generate_Y_matrix(struc)
    print("\n\nY matrix:")
    print(Y)
    
    V_bc = zeros([len(struc["conductors"])])
    V_bc[0] = 1
    #V_bc[1] = 1
    Q = calc_Q(struc, Y_inv, seg_struc, V_bc, plot=args.plot)
    print("\n\nQ Sim:")
    print(Q)
    
    cond = struc["conductors"][0]
    d = cond["pos"][1]
    a = cond["diam"]/2
    Q_ideal = 2*pi*e0/arccosh(d/a)
    print("\nQ Ideal:")
    print(Q_ideal)
    print("\n\n")
    
    C_struc = calc_C(struc, Y_inv, seg_struc)
    print("\nCapacitance Structure [F/m]")
    print(C_struc)
    
    L_struc = calc_L(C_struc)
    print("\nInductance Structure  [H/m]")
    print(L_struc)
    