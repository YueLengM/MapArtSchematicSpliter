#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from copy import deepcopy
import sys
from os import path

from nbtlib import File
from nbtlib.schema import schema
from nbtlib.tag import Compound, Double, Int, List, String

Structure = schema(
    'Structure', {
        'DataVersion':
        Int,
        'author':
        String,
        'size':
        List[Int],
        'palette':
        List[schema('State', {
            'Name': String,
            'Properties': Compound,
        })],
        'blocks':
        List[schema('Block', {
            'state': Int,
            'pos': List[Int],
            'nbt': Compound,
        })],
        'entities':
        List[schema('Entity', {
            'pos': List[Double],
            'blockPos': List[Int],
            'nbt': Compound,
        })],
    })


class StructureFile(File, schema('StructureFileSchema', {'': Structure})):
    def __init__(self, structure_data=None):
        super().__init__({'': structure_data or {}})
        self.gzipped = True

    @classmethod
    def load(cls, filename, gzipped=True):
        return super().load(filename, gzipped)


# container template for each file
chunk = {'size': [0, 0, 0], 'palette': [], 'blocks': []}

# common part of every file
common = {'DataVersion': 0, 'author': 'splited mapartcraft', 'entities': []}

# stores mapartcraft nbt data
data = {}

file = sys.argv[1]

print('Loading nbt file')
with StructureFile.load(file) as structure_file:
    data = structure_file.root

print('Analazing')
common['DataVersion'] = int(data['DataVersion'])

split_col = (data['size'][0] // 128)
split_row = (data['size'][2] // 128)
split_size = split_col * split_row

print('Map size: {}x{}'.format(split_col, split_row))
print('Art height: {} blocks'.format(data['size'][1] + 1))

confirm = input('Start process? [y]/n: ')
if confirm == 'n':
    exit(0)

print('Processing')
chunks = [deepcopy(chunk) for _ in range(split_size)]
palette_dict = [{} for _ in range(split_size)]
max_height = [0 for _ in range(split_size)]

for i, area in enumerate(chunks):
    if i % split_col == 0:
        # Maps on the first row hava a additional layer to draw shadow on the first line of pixel.
        area['size'] = [128, 0, 128 + 1]
    else:
        area['size'] = [128, 0, 128]

for b in data['blocks']:
    # x coordinate
    col = divmod(b['pos'][0], 128)
    # z coordinate
    row = divmod(b['pos'][2] - 1, 128)
    if row[0] == -1:
        row = (0, -1)
    # which map the block at
    split_index = row[0] + col[0] * split_row

    y = int(b['pos'][1])
    max_height[split_index] = max(max_height[split_index], y)

    block = data['palette'][int(b['state'])]['Name']
    # remapping palette to reduce palette size

    if block in palette_dict[split_index]:
        maped_state = palette_dict[split_index][block]
    else:
        maped_state = len(palette_dict[split_index])
        palette_dict[split_index][block] = maped_state
        # The Properties for the block will be dropped here.
        chunks[split_index]['palette'].append({'Name': block})

    chunks[split_index]['blocks'].append({
        'pos': [col[1], y, row[1]],
        'state': maped_state
    })

for i in range(split_size):
    print('Generating file {} of {}'.format(i + 1, split_size))
    # add other data back
    chunks[i]['size'][1] = max_height[i] + 1
    chunks[i]['DataVersion'] = common['DataVersion']
    chunks[i]['author'] = common['author']
    chunks[i]['entities'] = common['entities']

    res = StructureFile(chunks[i])
    res.save('{}_{}.nbt'.format(path.splitext(file)[0], i))

print('Done')
