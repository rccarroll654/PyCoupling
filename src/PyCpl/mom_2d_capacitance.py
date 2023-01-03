from numpy import *
import json

e0 = 8.854e-12 # F/m
c_light = 2.998e8 # m/s

# Convert
def scale_SI(unit):
    if unit == "mm":
        f = 1e-3
    elif unit == "um":
        f = 1e-6
    elif unit == "cm":
        f = 1e-2
    elif unit == "m":
        f = 1
    elif unit == "km":
        f = 1e3
    elif unit == "mil":
        f = (1e-3)/39.37
    elif unit == "in":
        f = 1/39.37
    elif unit == "ft":
        f = 12/39.37
    return f

def load_struc_file(fn):
    fh = open(fn, 'r')
    txt = ""
    for line in fh.readlines():
        txt += line
    struc = json.loads(txt)
    return struc

"""
Generate structure object with preprocessing.
"""
def generate_struct_obj(fn):
    sf = load_struc_file(fn)
    
    # Apply default settings
    N = sf["mesh"]["min-div"]
    for c in sf["conductors"]:
        c["N"] = N
    
    return sf

"""
Kernel of a flat charge distribution in 2D
    r_prb: Cartesian coordinates of probe point, list[2]
    r_src: Cartesian coordinates of source mid point, list[2]
    x_vec: Direction along charge distribution, list[2]
    length: length of charge distribution (meters), float
"""
def kernel_flat(r_prb, r_src, x_vec, length):
    # Transform and rotate into source frame
    r1 = array(r_prb) - array(r_src)
    phi = arctan2(x_vec[1], x_vec[0])
    x_hat = array([cos(phi), sin(phi)])
    y_hat = array([-sin(phi), cos(phi)])
    x = dot(r1, x_hat)
    y = dot(r1, y_hat)
    # Calculated kernel
    a = length/2
    k = (a-x)*log((a-x)**2+y**2)-2*y*arctan2(y, a-x) - 2*a
    a = -length/2
    k -= (a-x)*log((a-x)**2+y**2)-2*y*arctan2(y, a-x) - 2*a
    return -k/(4*pi*e0)

"""
Kernel of a flat charge distribution in 2D, with ground plane at x=0
    r_prb: Cartesian coordinates of probe point, list[2]
    r_src: Cartesian coordinates of source mid point, list[2]
    x_vec: Direction along charge distribution, list[2]
    length: length of charge distribution (meters), float
"""
def kernel_flat_gp(r_prb, r_src, x_vec, length):
    # Find mirrored vectors
    r_src_mir = [r_src[0], -r_src[1]]
    x_vec_mir = [x_vec[0], -x_vec[1]]
    # Get kernel
    k =  kernel_flat(r_prb, r_src, x_vec, length)
    k -= kernel_flat(r_prb, r_src_mir, x_vec_mir, length)
    return k

"""
Kernel of a flat charge distribution in 2D, induced charge buildup on dielectric interface
    r_prb: Cartesian coordinates of probe point, list[2]
    r_src: Cartesian coordinates of source mid point, list[2]
    x_vec: Direction along charge distribution, list[2]
    length: length of charge distribution (meters), float
    e1: dielectric constant in -x direction
    e2: dielectric constant in +x direction
    dx: Differential step in +/-x direction divided by length
"""
def kernel_flat_dielectric_surf(r_prb, r_src, x_vec, length, e1, e2, dx=0.01):
    # Transform and rotate into source frame
    r1 = array(r_prb) - array(r_src)
    phi = arctan2(x_vec[1], x_vec[0])
    x_hat = array([cos(phi), sin(phi)])
    y_hat = array([-sin(phi), cos(phi)])
    x = dot(r1, x_hat)
    y = dot(r1, y_hat)
    # Calculated kernel, -x direction
    a = length/2
    k1 = (a-x+dx*length)*log((a-x+dx*length)**2+y**2)-2*y*arctan2(y, a-x+dx*length) - 2*a
    a = -length/2
    k1 -= (a-x+dx*length)*log((a-x+dx*length)**2+y**2)-2*y*arctan2(y, a-x+dx*length) - 2*a
    # Calculated kernel, +x direction
    a = length/2
    k2 = (a-x-dx*length)*log((a-x-dx*length)**2+y**2)-2*y*arctan2(y, a-x-dx*length) - 2*a
    a = -length/2
    k2 -= (a-x-dx*length)*log((a-x-dx*length)**2+y**2)-2*y*arctan2(y, a-x-dx*length) - 2*a
    return (e1+e2)*(e2-e1)/(e1*e2*8*pi)*(k2-k1)/(2*dx*length)

"""
Get Y matrix from structure
"""
def generate_Y_matrix(struc):
    seg_struc = []
    cond = struc["conductors"]
    for icon, c in enumerate(cond):
        for iseg in range(c["N"]):
            seg_struc.append([icon, iseg])
    
    M = len(seg_struc)
    Y = zeros([M, M])
    for icol, seg_col in enumerate(seg_struc):
        scale_src = scale_SI(cond[seg_col[0]]["units"])
        pos_src = array(cond[seg_col[0]]["pos"])*scale_src
        r_mag_src = cond[seg_col[0]]["diam"]/2*scale_src
        
        # Calc source
        dphi = 2*pi/cond[seg_col[0]]["N"]
        L = r_mag_src*sin(dphi/2)*(1+cos(dphi/2))
        r_src = pos_src + r_mag_src*array([cos(dphi*seg_col[1]), sin(dphi*seg_col[1])])
        x_vec = [-sin(dphi*seg_col[1]), cos(dphi*seg_col[1])]
        
        for irow, seg_row in enumerate(seg_struc):
            scale_prb = scale_SI(cond[seg_row[0]]["units"])
            pos_prb = array(cond[seg_row[0]]["pos"])*scale_prb
            r_mag_prb = cond[seg_row[0]]["diam"]/2*scale_prb
            
            # Calc Probe
            dphi = 2*pi/cond[seg_row[0]]["N"]
            r_prb = pos_prb + r_mag_prb*array([cos(dphi*seg_row[1]), sin(dphi*seg_row[1])])
            
            Y[irow][icol] = kernel_flat_gp(r_prb, r_src, x_vec, L)
    Y_inv = linalg.inv(Y)
    return Y, Y_inv, seg_struc

def plot_seg(Q_seg, struc, seg_struc, N=101, title=""):
    import matplotlib.pyplot as plt
    size = [0]*4
    cond = struc["conductors"]
    for seg in seg_struc:
        pos = cond[seg[0]]["pos"]
        diam = cond[seg[0]]["diam"]
        scale = scale_SI(cond[seg[0]]["units"])
        size[0] = min(size[0], scale*(pos[0]-diam))
        size[1] = max(size[1], scale*(pos[0]+diam))
        size[2] = min(size[2], scale*(pos[1]-diam))
        size[3] = max(size[3], scale*(pos[1]+diam))
    Y, X = meshgrid(linspace(size[2], size[3], N), linspace(size[0], size[1], N))
    
    Z = zeros([N-1,N-1])

            
    for ind, seg in enumerate(seg_struc):
        scale = scale_SI(cond[seg[0]]["units"])
        pos = array(cond[seg[0]]["pos"])*scale
        r_mag = cond[seg[0]]["diam"]/2*scale
        
        # Calc source
        dphi = 2*pi/cond[seg[0]]["N"]
        L = r_mag*sin(dphi/2)*(1+cos(dphi/2))
        r = pos + r_mag*array([cos(dphi*seg[1]), sin(dphi*seg[1])])
        x_vec = [-sin(dphi*seg[1]), cos(dphi*seg[1])]
        
        for ix in range(N-1):
            for iy in range(N-1):
                x = X[ix,iy]
                y = Y[ix,iy]
                Z[ix,iy] += Q_seg[ind]*kernel_flat_gp([x,y], r, x_vec, L)
                
    fig, ax = plt.subplots()
    
    z_min, z_max = Z.min(), Z.max()
    
    c = ax.pcolormesh(X, Y, Z, cmap='RdBu', vmin=z_min, vmax=z_max)
    ax.set_title(title)
    # set the limits of the plot to the limits of the data
    ax.axis([X.min(), X.max(), Y.min(), Y.max()])
    fig.colorbar(c, ax=ax)

    plt.show()

"""
Solve for total charge Q given structure and boundary conditions.
"""
def calc_Q(struc, Y_inv, seg_struc, V_bc, plot=False):
    V_seg = []
    for seg in seg_struc:
        V_seg.append(V_bc[seg[0]])
    Q_seg = matmul(Y_inv, V_seg)
    Q = zeros([len(V_bc)])
    for i, seg in enumerate(seg_struc):
        cond = struc["conductors"][seg[0]]
        scale = scale_SI(cond["units"])
        r_mag = cond["diam"]/2*scale
        dphi = 2*pi/cond["N"]
        L = r_mag*sin(dphi/2)*(1+cos(dphi/2))
        Q[seg[0]] += Q_seg[i]*L
    if plot:
        plot_seg(Q_seg, struc, seg_struc, N=101)
    return Q

"""
Solve for inter capacitance matrix.
"""
def calc_C(struc, Y_inv, seg_struc):
    C_struc = []
    N = len(struc["conductors"])
    for ir in range(N):
        # Intial baseline, primary wire on
        #C_sol = zeros([N, N])
        V_bc = zeros([N])
        V_bc[ir] = 1
        
        # Apply correction
        Q = calc_Q(struc, Y_inv, seg_struc, V_bc)
        
        C_struc.append(Q)
    
    return array(C_struc)

"""
Solve for inductance matrix
"""
def calc_L(C_fs):
    L_struc = linalg.inv(C_fs)/(c_light**2)
    return L_struc

