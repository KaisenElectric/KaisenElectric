from odoo import models, fields, api, _
from hashlib import sha256


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _post_pdf(self, save_in_attachment, pdf_content=None, res_ids=None):
        if self.model == 'account.move' and res_ids and len(res_ids) == 1 and pdf_content:
            record_id = self.env['account.move'].browse(res_ids)
            doc_hash = sha256(record_id.string_to_hash.encode('utf-8')).hexdigest()
            if doc_hash != record_id.message_main_attachment_hash:
                save_in_attachment.pop(res_ids[0], None)
                record_id.message_main_attachment_hash = doc_hash
                record_id.message_main_attachment_id = False

        return super(IrActionsReport, self)._post_pdf(save_in_attachment, pdf_content=pdf_content, res_ids=res_ids)
