"""An exact-xref display toggle must not hide other same-name mask groups."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import investigate_fema_map_mask as method


class MaskDisplayTests(unittest.TestCase):
    def test_only_selected_mask_changes_and_restore_is_exact(self):
        doc=fitz.open()
        doc.new_page(width=100,height=100);doc.new_page(width=100,height=100)
        first=doc.add_ocg('MASK');second=doc.add_ocg('MASK')
        for i,oc in enumerate([first,second]):
            doc[i].draw_rect(fitz.Rect(0,0,100,100),color=None,fill=(1,0,0))
            doc[i].draw_rect(fitz.Rect(0,0,100,100),color=None,fill=(1,1,1),oc=oc)
        doc.set_layer(-1,on=[],off=[])  # Match the source PDF's implicit default-ON state.
        original=doc.tobytes();doc=fitz.open(stream=original,filetype='pdf')
        baseline=[doc[i].get_pixmap().samples for i in [0,1]]
        with patch.object(method,'MASK',first):
            view=method.hidden_view(doc)
        self.assertEqual(view.get_layer(),{'off':[first]})
        self.assertNotEqual(view[0].get_pixmap().samples,baseline[0])
        self.assertEqual(view[1].get_pixmap().samples,baseline[1])
        view.set_layer(-1,on=[first],off=[])
        restored=fitz.open(stream=view.tobytes(),filetype='pdf')
        self.assertEqual(restored[0].get_pixmap().samples,baseline[0])
        self.assertEqual(restored[1].get_pixmap().samples,baseline[1])
        # Reopening the original bytes retains its published display.
        fresh=fitz.open(stream=original,filetype='pdf')
        self.assertEqual(fresh[0].get_pixmap().samples,baseline[0])


if __name__=='__main__':unittest.main()
