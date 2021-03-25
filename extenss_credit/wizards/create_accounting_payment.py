from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import Warning, UserError, ValidationError

class CreateAccountingPayment(models.TransientModel):
    _name = 'extenss.credit.accounting_payments'
    _description = 'Account Movements'

    accnt_mov_id = fields.Many2one('extenss.credit.account', string='Account', tracking=True, translate=True)
    movement_type = fields.Selection([('cargo','Charge'),('abono','Credit')], string='Movement type', tracking=True, translate=True)
    amount = fields.Monetary(string='Amount', currency_field='company_currency', tracking=True ,translate=True)
    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    def action_create_movement(self):
        accnt = self.env['extenss.credit.account'].browse(self.env.context.get('active_ids'))
        self.action_apply_movement(accnt.id, self.movement_type, self.amount, '')

    def action_apply_movement(self, id, type_movement, amount, comment):
        ca = self.env['extenss.credit.account'].search([('id', '=', id)])
        cm = self.env['extenss.credit.movements']
        if ca:
            for record in ca:
                inicial_balance = round(record.balance,2)
                if type_movement == 'cargo':
                    end_balance = record.balance - amount
                if type_movement == 'abono':
                    end_balance = record.balance + amount
                end_balance=round(end_balance,2)
                if end_balance < 0:
                    if end_balance>-.05:
                        end_balance=0
                    else:
                        raise ValidationError(_('The final balance cannot be negative'))

                cm.create({
                    'accnt_mov_id': id,
                    'date_time_move': datetime.now(),
                    'movement_type': type_movement,
                    'amount': amount,
                    'initial_balance': inicial_balance,
                    'ending_balance': end_balance,
                    'comments': comment, 
                })
                record.balance = end_balance
            return "Ok"

        else:
            return "Account not found"