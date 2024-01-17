import numpy as np
from scipy.ndimage import binary_fill_holes
from scipy.ndimage import distance_transform_edt as distance
from skimage import measure
import trimesh
import os
from itertools import combinations_with_replacement
from helpers import load_config

# load the configuration file
config = load_config()

corner_stls = config["corner_stls"]
ENABLE_CUDA = config["ENABLE_CUDA"]
ENABLE_RAY_SAMPLING = config["ENABLE_RAY_SAMPLING"]
THREADS_PER_BLOCK = config["THREADS_PER_BLOCK"]
resolution = config["resolution"]
project_dir = config["project_dir"]
samples_per_dim = config["samples_per_dim"]

def generate_barycentric_coordinates(num_dimensions, steps):
    # generate all combinations with replacement to ensure all sums are <= 1
    comb = combinations_with_replacement(range(steps), num_dimensions)
    valid_coords = [np.array(c) / (steps - 1) for c in comb if sum(c) <= (steps - 1)]
    return valid_coords

def interpolate_sdfs(sdfs, coords):
    interpolated_sdf = np.zeros_like(sdfs[0])
    for i, coord in enumerate(coords):
        interpolated_sdf += coord * sdfs[i]
    interpolated_sdf += (1 - sum(coords)) * sdfs[-1]
    return interpolated_sdf

sdfs = [binary_fill_holes(np.load(f"{config['project_dir']}/corner_{i}.npy")) for i in range(len(corner_stls))]
sdfs = [distance(~sdf) - distance(sdf) for sdf in sdfs]

# generate barycentric coordinates
num_stls = len(config["corner_stls"])
barycentric_coords = generate_barycentric_coordinates(num_stls - 1, samples_per_dim)

os.makedirs(f"{config['project_dir']}/sdfs", exist_ok=True) 
output_dir = f"{config['project_dir']}/sdfs"

# process each combination of barycentric coordinates
for coords in barycentric_coords:
    interpolated_sdf = interpolate_sdfs(sdfs, coords)
    
    epsilon = 1.0
    # TODO: revisit marching cubes
    interface = (interpolated_sdf >= -epsilon) & \
                (interpolated_sdf <= epsilon)
    scalar_field = interface.astype(np.float32)
    # extract interface using marching cubes
    vertices, faces, normals, values = measure.marching_cubes(scalar_field, level=0.5)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

    # export mesh
    coords_str = '_'.join(f"{int(coord * 100)}" for coord in coords)
    filename = f"{output_dir}/sdf_{coords_str}.stl"
    
    print(f'Watertightness check: {mesh.is_watertight}')
    mesh.export(filename)

