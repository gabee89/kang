import json
import struct
import unittest
from pathlib import Path
from defense import CATALOG, MAP


class AssetTests(unittest.TestCase):
    def test_local_animation_atlases_are_complete_pngs(self):
        root=Path(__file__).parent/'assets'/'sprites'
        manifest=json.loads((root/'manifest.json').read_text())
        self.assertEqual(len(manifest),31)
        for dex in set(CATALOG)|{19,41,46,74,23,48,66,111,52,95,149}:
            item=manifest[str(dex)]
            self.assertGreater(item['frames'],1)
            for path,width in ((root/f'{dex}.png',item['frames']*96),(root/'portraits'/f'{dex}.png',96)):
                data=path.read_bytes()
                self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n')
                self.assertEqual(struct.unpack('>II',data[16:24]),(width,96))

    def test_36_slots_do_not_overlap(self):
        self.assertEqual(len(MAP['cells']),36)
        self.assertEqual(len(MAP['terrain']),36)
        for i,(x,y) in enumerate(MAP['cells']):
            for a,b in MAP['cells'][i+1:]:
                self.assertTrue(abs(x-a)*77>=MAP['tileWidth'] or abs(y-b)*76>=MAP['tileHeight'])

