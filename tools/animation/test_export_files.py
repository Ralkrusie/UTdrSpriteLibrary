import unittest
from export_files import named_entries
from encoder import filename, export_filename


class ExportNames(unittest.TestCase):
    def test_collisions_are_unique_and_selection_order_independent(self):
        variants = [dict(id=str(i), name=name, chapters=[2], frames=[])
                    for i, name in enumerate(('spr/name', 'spr?name', 'SPR_NAME', 'spr_name'))]
        forward = named_entries([(None, v) for v in variants])
        backward = named_entries([(None, v) for v in reversed(variants)])
        names = {v['id']: filename(v) for _, v in forward}
        self.assertEqual(len({name.casefold() for name in names.values()}), len(variants))
        self.assertEqual(names, {v['id']: filename(v) for _, v in backward})
        self.assertEqual(names['0'], 'spr_name_Ch2')
        self.assertEqual(names['1'], 'spr_name_Ch2_2')

    def test_package_metadata_cannot_override_export_paths(self):
        v = dict(id='one', name='spr_name', chapters=[1], export_name='../../outside')
        named = named_entries([(None, v)])[0][1]
        self.assertEqual(filename(named), 'spr_name_Ch1')
        self.assertNotIn('/', filename(v))

    def test_parameter_names_match_effective_output(self):
        v = dict(name='spr_name', chapters=[2])
        for fmt in ('gif', 'apng', 'mov'):
            self.assertEqual(export_filename(v, dict(format=fmt, scale=5, fps=3.75)), 'spr_name_Ch2_3.75fps_5x')
        self.assertEqual(export_filename(v, dict(format='mov', scale=1.5, fps=6.3)), 'spr_name_Ch2_6.3fps_1.5x')
        self.assertEqual(export_filename(v, dict(format='png', scale=5, fps=3.75)), 'spr_name_Ch2_5x')
        self.assertEqual(export_filename(v, dict(format='png', scale=5, fps=3.75, original=True)), 'spr_name_Ch2_original_1x')


if __name__ == '__main__':
    unittest.main()
