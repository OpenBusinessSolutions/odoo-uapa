# -*- coding: utf-8 -*-
"""
Created on Mon Jul  1 18:23:26 2013

@author: Carlos Llamacho.
"""
import datetime
#import time
#from datetime import date
#from datetime import datetime
#from datetime import timedelta
from dateutil import relativedelta
from openerp import tools
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

from openerp.tools.safe_eval import safe_eval as eval
from openerp.osv import osv, fields


class HrEmployee(osv.osv):
    """Class that inherits from hr.employee and extends the model with 4 fields."""
    _name='hr.employee'
    _inherit='hr.employee'
    _columns = {
    'salary_scale_category':fields.selection((('1','1'),
        ('2','2'),
        ('3','3'),
        ('4','4'),
        ('5','5'),
        ('6','6'),
        ('7','7'),
        ('8','8'),
        ('9','9'),
        ('10','10'),
        ('11','11'),
        ('12','12'),
        ('13','13'),
        ('14','14'),
        ('15','15'),
        ('16','16'),
        ('17','17'),
        ('18','18'),
        ('19','19'),
        ('20','20'),
        ('21','21'),
        ('22','22'),
        ('23','23'),
        ('24','24'),
        ('25','25')), 'Salary Scale Category'),
    'salary_scale_level':fields.selection((('1','1'),
        ('2','2'),
        ('3','3'),
        ('4','4'),
        ('5','5'),
        ('6','6')), 'Salary Scale Level'),
    'personnel_actions_ids':fields.one2many('hr.personnel.action',
                                            'employee_id',
                                            'Personnel actions'),
    'transfer_to':fields.selection((
                                         ('1','UAPA Santiago'),
                                         ('2','UAPA Santo Domingo'),
                                         ('3','UAPA Nagua'),
                                         ('4','CEGES Santo Domingo'),
                                         ('5','CEGES Santiago')), 'Transfererido a '),
    'on_vacation':fields.boolean('On vacation'),
    'on_licence':fields.boolean('On licence'),
    'proposed_misconduct':fields.text('Amonestacion'),
    'proposed_misconduct_level':fields.selection((('1','1'),
                                                    ('2','2'),
                                                    ('3','3')), 'Nivel falta cometida'),
    }

HrEmployee()

class HrContract(osv.osv):
    """Class extends the hr.contract model with 1 field."""
    _name="hr.contract"
    _inherit="hr.contract"
    _columns = {
        'diff_scale':fields.float('Diff. Scale', size=16),
        }

HrContract()

class HrPersonnelAction(osv.osv):
    """Create a new model that stores all personnel actions.
    
    Inherit: hr_personnel_action
    """
    _name='hr.personnel.action'
    _description="Hr Personnel Action"  

    def get_wage(self, cr, uid, employee_id, context=None):
        hr_contract_obj = self.pool.get('hr.contract')
        hr_obj = self.pool.get('hr.employee')

        if employee_id:
            hr_cont_id = hr_contract_obj.search(cr, uid, [('employee_id','=',employee_id)], order='id', context = None)

            emp_cont = hr_contract_obj.browse(cr, uid, hr_cont_id[-1], context=None)
            return {'value': {'proposed_wage':emp_cont.wage}}
        else:
            return {}

    def calc_actual_total(self, cr, uid, ids, field_name, args, context=None):
        """Calculates the sum of the wage and the diff_scale

        Returns: Dictionary{id:value}"""
        
        result = {}
        for record in self.browse(cr, uid, ids, context=None):
            result[record.id] = record.actual_diff_scale + record.actual_wage
        return result
        
    def calc_proposed_total(self, cr, uid, ids, field_name, args, context=None):
        """Calculates the sum of the wage and the diff_scale
    
        Returns: Dictionary{id:value}"""
        result = {}
        records = self.browse(cr, uid, ids, context=None)
        for record in records:
            result [record.id] = record.proposed_wage + record.proposed_diff_scale
        return result

    def calc_employee_leave_total(self, cr, uid, ids, field_name, args, context=None):
        """Calculates the sum of the 3 fields of employee benefits.
        
        Returns Dictionary{id:value}"""
        result = {}
        records = self.browse(cr, uid, ids, context=None)
        for record in records:
            result[record.id] = record.severance + record.forewarning + record.christmas_salary
        return result
        
    def calc_number_of_days(self, cr, uid, ids, from_date, to_date, context=None):
        """Calculates the time beetwen two dates.

        Arguments:
        from_date -- start date, type string
        to_date -- end date, type string
        
        Returns: integer"""
        to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d')
        from_date = datetime.datetime.strptime(from_date, '%Y-%m-%d')
        to_date = datetime.date(to_date.year, to_date.month, to_date.day)
        from_date = datetime.date(from_date.year, from_date.month, from_date.day)
        days = to_date - from_date
        #d = ''
	num_of_days = str(days)[:-14]
        #for i in str(days):
        #    if i == '0':
        #        d = 0
        #        break
        #    elif i == ' ':
        #        break
        #    else:
        #        d += i
        return int(num_of_days)
    
    def get_actions_ids(self, cr, uid, context=None):
        actions_ids = self.search(cr, uid, [('states','=','approved')], context=None)
        return actions_ids
    
    def run_personnel_actions(self, cr, uid, ids=None, context=None):
        """Runs a determined action on the date set in the field effective_date.
        Returns None"""
        
        #If the code is called from the form, ids is the id of the record active.
        #If is called from the cron job, this function get all records ids.        

	if not ids:
            ids = self.get_actions_ids(cr, uid, context=None)
	ret = {}
        for contract in self.read(cr, uid, ids, ['contract_id'], context=context):
            ret = contract
        #This variables holds the objects we are going to be using in each action.
        hr_obj = self.pool.get('hr.employee')
        hr_cont_obj = self.pool.get('hr.contract')
        hr_holiday = self.pool.get('hr.holidays')
        hr_pay_obj = self.pool.get('hr.payslip')
        hr_payslip_obj = self.pool.get('hr.payslip.input')
       
        #List with all the records for the object hr.personnel.action
        #actions_ids = self.search(cr, uid, [('states','=','approved')], context=None)
        #Object that access all the records. actions_ids is the list with all my ids.
        actions = self.browse(cr, uid, ids, context=None)
        
        #Loop for traversing all records in the hr.personnel.action table and if the status is for approved and the date is today, run them.
        for action in actions:
        #These variables hold the ids of the contract and payroll associated to the employee.
            hr_cont_id = hr_cont_obj.search(cr, uid, [('employee_id', '=', action.employee_id.id)],
                                            order='id', context=None)
            hr_pay_id = hr_pay_obj.search(cr, uid, [('employee_id', '=', action.employee_id.id)],
                                          order='id', context=None)
          
            #This converts the date of the record to a format that can be evaluated.
            effective_date = datetime.datetime.strptime(action.effective_date, '%Y-%m-%d')
            effective_date = datetime.date(effective_date.year, effective_date.month, effective_date.day)
            
            #If the function is called from the button and the date is not the correct, raise exception.
            if ids and effective_date != datetime.date.today():
                raise osv.except_osv('Error', 'This employee action is not scheduled for applying today.')
            #If the record is set up to be applied today is applied.
            if effective_date == datetime.date.today():
                if action.action_requested == '1':
                    hr_payslip_obj.create(cr, uid, {'contract_id':ret['contract_id'][0],
                                                    'amount':action.proposed_bonus,
                                                    'name':"Bonus payment",
                                                    'code':1,
                                                    'payslip_id':hr_pay_id[0]}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)

		#Action - Probatory period dismissal
                elif action.action_requested == '2':
                    hr_obj.write(cr, uid, action.employee_id.id, {'active':False}, context=None)
                    hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'trial_date_end':action.effective_date}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)
                #Action - Position changes.
                elif action.action_requested == '3':
                    hr_obj.write(cr, uid, action.employee_id.id, {'department_id':action.proposed_dependency.id,
                                                                  'job_id':action.proposed_ocupation.id,
                                                                  'parent_id':action.proposed_parent_id.id}, context=None)
                    hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'working_hours':action.proposed_orderly_turn.id,
                                                             'wage':action.proposed_total}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)
                #Action - Command line correction
                elif action.action_requested == '4':
                    hr_obj.write(cr, uid, action.employee_id, {'parent_id':action.proposed_parent_id.id}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)
                #Actions - Decease and terminations unjustified. This is supposed to have benefits.
                elif action.action_requested == '5'  or action.action_requested == '7' or action.action_requested == '8':
                    hr_obj.write(cr, uid, action.employee_id.id, {'active':False}, context=None)
                    hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'date_end':action.effective_date}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)
                #Actions - Justified termination. This is also supposed to have benefits.
                elif action.action_requested == '6':
                    hr_obj.write(cr, uid, action.employee_id.id, {'active':False}, context = None)
                    hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'date_end':action.effective_date}, context = None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)
                #Action - Incorporation
                elif action.action_requested == '9':
                    hr_obj.write(cr, uid, action.employee_id.id, {'active':True,
                                                                  'on_vacation':False,
                                                                  'on_licence':False}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)
                #Action - Licence with payment.
                elif action.action_requested == '10':
                    cr.execute("SELECT date_to FROM hr_holidays WHERE employee_id IN ({0}) ORDER BY id DESC LIMIT 1".format(action.employee_id.id))
                    res = cr.fetchmany()
		    if len(res) == 0:
                        hr_obj.write(cr, uid, action.employee_id.id, {'on_licence':True}, context=None)
                        hr_holiday.write(cr, uid, action.id, {'state':'validate',
                                                'holiday_status_id':5,
                                                'employee_id':action.employee_id.id,
                                                'department_id':action.proposed_dependency.id,
                                                'holiday_type':'employee',
                                                'date_from':action.effective_date,
                                                'date_to':action.end_of_leave,
						'number_of_days_temp':self.calc_number_of_days(cr, uid, ids, action.effective_date, action.end_of_leave)}, context=None)
                        self.write(cr, uid, action.id, {'states':'applied'}, context=None)
		    else:
			self.write(cr, uid, ids,{'states': 'cancelled'}, context=None)
			raise osv.except_osv(_('Error'), _('Este empleado cuenta con vacaciones asignadas!'))#return False
                #Action - Maternity Licence.
                elif action.action_requested == '11':
                    cr.execute("SELECT date_to FROM hr_holidays WHERE employee_id IN ({0}) ORDER BY id DESC LIMIT 1".format(action.employee_id.id))
                    res = cr.fetchmany()
                    if len(res) == 0:
                        hr_obj.write(cr, uid, action.employee_id.id, {'on_licence':True}, context=None)
                        hr_holiday.create(cr, uid, {'state':'validate',
                                                'holiday_status_id':6,
                                                'employee_id':action.employee_id.id,
                                                'department_id':action.proposed_dependency.id,
                                                'holiday_type':'employee', 
                                                'date_from':action.effective_date,
                                                'date_to':action.end_of_leave,
                                                'number_of_days_temp':self.calc_number_of_days(cr, uid, ids, action.effective_date, action.end_of_leave)}, context=None)
                        self.write(cr, uid, action.id, {'states':'applied'}, context=None)
		    else:
			self.write(cr, uid, ids,{'states': 'cancelled'}, context=None)
                        raise osv.except_osv(_('Advertencia'), _('Este empleado cuenta con vacaciones asignadas!'))
                #Action - Promotion
                elif action.action_requested == '12':
                    hr_obj.write(cr, uid, action.employee_id.id, {'job_id':action.proposed_ocupation.id,
                                                                  'salary_scale_category':action.proposed_salary_scale_category,
                                                                  'salary_scale_level':action.proposed_salary_scale_level}, context=None)
                    hr_cont_obj.write(cr, uid, ret['contract_id'][0],{'working_hours':action.proposed_orderly_turn.id,
                                                                'wage':action.proposed_total}, context=None)
	        #Action - Promotion and transference
                elif action.action_requested == '13':
                    hr_obj.write(cr, uid, action.employee_id.id, {'department_id':action.proposed_dependency.id,
                                                                  'job_id':action.proposed_ocupation.id,
                                                                  'salary_scale_category':action.proposed_salary_scale_category,
                                                                  'salary_scale_level':action.proposed_salary_scale_level}, context=None)
                    hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'working_hours':action.proposed_orderly_turn.id, 
                                                                #'diff_scale':action.proposed_diff_scale, 
                                                                'wage':action.proposed_total}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)
                #Action - Wage changes
                elif action.action_requested == '14':
		    hr_obj.write(cr, uid, action.employee_id.id, {'salary_scale_category':action.proposed_salary_scale_category,
                                                                  'salary_scale_level':action.proposed_salary_scale_level}, context=None)
                    hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'wage':action.proposed_total,                                                              'diff_scale':action.proposed_diff_scale}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)
                #Action - Position reclasification - Changes all but department_id
                elif action.action_requested == '15':
                    hr_obj.write(cr, uid, action.employee_id.id, {'job_id':action.proposed_ocupation.id,
                                                                  'salary_scale_category':action.proposed_salary_scale_category,
                                                                  'salary_scale_level':action.proposed_salary_scale_level}, context=None)
                    hr_cont_obj.write(cr, uid, ret['contract_id'][0], {#'diff_scale':action.proposed_diff_scale, 
                                                                'working_hours':action.proposed_orderly_turn.id, 
                                                                'wage':action.proposed_wage + action.proposed_diff_scale,
                    						'start_date':action.effective_date,
          		                                        'contract_id':hr_cont_id[-1]}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)
                #Action - Position reclasification with department changes
                elif action.action_requested == '16':
                    hr_obj.write(cr, uid, action.employee_id.id, {'department_id':action.proposed_dependency.id,
								  'job_id':action.proposed_ocupation.id,
                                                                  'salary_scale_category':action.proposed_salary_scale_category,
	                                                          'salary_scale_level':action.proposed_salary_scale_level,
								  'parent_id':action.proposed_parent_id.id
								  }, context=None)
	                
                    hr_cont_obj.write(cr, uid, ret['contract_id'][0], {#'diff_scale':action.proposed_diff_scale,
                                                                'working_hours':action.proposed_orderly_turn.id, 
                                                                'wage':action.proposed_wage + action.proposed_diff_scale}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)
                #Action - Reintregation with the company. Old contract.
                elif action.action_requested == '17':
                    hr_obj.write(cr, uid, action.employee_id.id, {'active':True,
                                                                  'department_id':action.proposed_dependency.id,
                                                                  'job_id':action.proposed_ocupation.id,
                                                                  'salary_scale_category':action.proposed_salary_scale_category,
                                                                  'salary_scale_level':action.proposed_salary_scale_level,
                                                                  'parent_id':action.proposed_parent_id.id
                                                                  #'coach_id':action.proposed_coach_id.id
								  }, context=None)
                    hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'date_start':action.effective_date,
								#'diff_scale':action.proposed_diff_scale,
                                                                'working_hours':action.proposed_orderly_turn.id, 
                                                                'wage':action.proposed_wage + action.proposed_diff_scale}, context=None)
		    hr_payslip_obj.create(cr, uid, {'contract_id':ret['contract_id'][0],
                                                    'amount':action.proposed_wage,
                                                    'name':"Reintegracion con viejo contracto",
                                                    'code':17,
                                                    'payslip_id':hr_pay_id[0]}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)
                #Action - Reintegration with a new contract.
                elif action.action_requested == '18':
                    hr_obj.write(cr, uid, action.employee_id.id, {'active':True,
                                                                  'department_id':action.proposed_dependency.id,
                                                                  'job_id':action.proposed_ocupation.id,   
                                                                  'salary_scale_category':action.proposed_salary_scale_category,
                                                                  'salary_scale_level':action.proposed_salary_scale_level,
                                                                  'parent_id':action.proposed_parent_id.id
                                                                  #'coach_id':action.proposed_coach_id.id
								  }, context=None)
                    hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'working_hours':action.proposed_orderly_turn.id,
                                                 'date_end':action.proposed_end_new_contract,
                                                 'employee_id':action.employee_id.id,
                                                 'name':"Standard new contract for {0}.".format(action.employee_id.name_related),
                                                 'date_start':action.effective_date,
                                                 'schedule_pay':'monthly',
                                                 #'diff_scale':action.proposed_diff_scale,
                                                 'struct_id':1,
                                                 'type_id':1,
                                                 'wage':action.proposed_wage + action.proposed_diff_scale}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)

		#Action - Disciplinary action.
		elif action.action_requested == '19':
                    hr_obj.write(cr, uid, action.employee_id.id, {
						'proposed_misconduct':action.proposed_misconduct,
						'proposed_misconduct_level':action.proposed_misconduct_level}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)

                #Action - Resignation
                elif action.action_requested == '20':
		    hr_cont_obj.write(cr, uid,ret['contract_id'][0], {'date_end':action.effective_date}, context=None)
                    cr.execute("select date_end from hr_contract where employee_id IN ({0}) ".format(action.employee_id.id))
	            res = cr.fetchmany()
                    if len(res) == 0:
		        hr_obj.write(cr, uid, action.employee_id.id, {'active':False}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)
                #Action - From temporary to permanent
                elif action.action_requested == '21':
                    hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'type_id':1}, context=None)

                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)
                #Action - Transference
                elif action.action_requested == '22':
                    hr_obj.write(cr, uid, action.employee_id.id, {}, context=None)
                    self.write(cr, uid, action.id, {'states':'applied'}, context=None)
                #Action - Vacations
                elif action.action_requested == '23':
		    cr.execute("SELECT date_to FROM hr_holidays WHERE employee_id IN ({}) ORDER BY id DESC LIMIT 1".format(action.employee_id.id))
	            res = cr.fetchmany() 
        	    if res[0][0][0:10] == action.end_of_leave:			
                        hr_obj.write(cr, uid, action.employee_id.id, {'on_vacation':True}, context=None)
                        hr_holiday.write(cr, uid, action.id, {'employee_id':action.employee_id.id,
                                                'department_id':action.proposed_dependency.id,
                                                'date_from':action.effective_date,
                                                'date_to':action.end_of_leave,
						'name':'Solicitud de vacaciones',
                                                'holiday_status_id':7,
                                                'number_of_days_temp':self.calc_number_of_days(cr, uid, ids, action.effective_date, action.end_of_leave), 'state':'validate'}, context=None)
                        self.write(cr, uid, action.id, {'states':'applied'},context=None)
                    else:
                        return False
		
    
          
    _columns={
    'origin_employee_id':fields.many2one('hr.employee', 'Petitioner', required=True, domain=[('manager','=',True)]),
    'origin_department_id':fields.many2one('hr.department', 'Area'),
    'origin_company_id':fields.many2one('res.company', 'Recinto'),
    'origin_address':fields.char('Address', size=128),
    'origin_state_id':fields.many2one('res.country.state', 'State'),
    'action_requested':fields.selection((#('1','Incentive allocation'),
                                         #('2', 'Probationary period dismissal'),
                                         ('3', 'Position change'),
                                         #('4', 'Command line correction'),
                                         ('5', 'Eviction'),
                                         ('6', 'Justified dismissal'),
                                         ('7', 'Deceased'),
                                         #('8', 'Inactivation'),
                                         ('9', 'Incorporation'),
                                         ('10', 'Licencia medica'),
                                         ('11', 'Licencia por maternidad'),
                                         ('12', 'Promotion'),
                                         #('13', 'Promotion and transference'),
                                         ('14', 'Salarial readjustment'),
                                         #('15', 'Position reclasification'),
                                         #('16', 'Reclasification and transference'),
                                         #('17', 'Reintegration with same contract'),
                                         #('18', 'Reintegration with new contract'),
                                         ('19', 'Amonestacion'),
                                         ('20', 'Resignation'),
                                         #('21', 'Temporary to permanent'),
                                         ('22', 'Transfer'),
                                         ('23', 'Vacations')), 'Action requested', required=True),
    'effective_date':fields.date('Effective date', required=True),
    'employee_id':fields.many2one('hr.employee', 'Petitioned', required=True),
    'contract_id': fields.many2one('hr.contract', 'Contracts', required=True),
    'actual_employee_code':fields.char('Code', size=32, readonly=True),
    'actual_identification_id':fields.char('Identification No.', size=32, readonly=True),
    'actual_dependency':fields.many2one('hr.department', 'Dependency', readonly=True),
    'actual_ocupation':fields.many2one('hr.job', 'Ocupation', readonly=True),
    'actual_parent_id':fields.many2one('hr.employee', 'Inmediate Superior'),
    #'actual_coach_id':fields.many2one('hr.employee', 'Coach'),
    'actual_orderly_turn':fields.many2one('resource.calendar', 'Actual work schedule'),
    'actual_salary_scale_category':fields.selection((('1','1'),
                                                  ('2','2'),
                                                  ('3','3'),
                                                  ('4','4'),
                                                     ('5','5'),
                                                     ('6','6'),
                                                     ('7','7'),
                                                     ('8','8'),
                                                     ('9','9'),
                                                     ('10','10'),
                                                     ('11','11'),
                                                     ('12','12'),
                                                     ('13','13'),
                                                     ('14','14'),
                                                    ('15','15'),
                                                     ('16','16'),
                                                     ('17','17'),
                                                     ('18','18'),
                                                     ('19','19'),
                                                     ('20','20'),
                                                     ('21','21'),
                                                     ('22','22'),
                                                     ('23','23'),
                                                     ('24','24'),
                                                     ('25','25')), 'Salary Scale Category'),
    'actual_salary_scale_level':fields.selection((('1','1'),
                                                  ('2','2'),
                                                  ('3','3'),
                                                  ('4','4'),
                                                  ('5','5'),
                                                  ('6','6')), 'Salary Scale Level'),
    'actual_wage':fields.float('Wage', digits=(16,2)),
    'actual_diff_scale':fields.float('Diff. scale', digits=(16,2)),
    'actual_total':fields.function(calc_actual_total, string='Actual Total', type='float'),
    'observations':fields.text('Observations'),
    'states':fields.selection((('draft', 'Draft'),
                               ('confirmed','Confirmed'),
                               ('approved','Approved'),
                               ('cancelled','Cancelled'),
                               ('applied', 'Applied')),'Status'),
    #'start_leave':fields.date('Start licence'),
    'end_of_leave':fields.date('End of licence'),
    'days_of_vacations':fields.integer('Cantidad de dias'),
    'proposed_dependency':fields.many2one('hr.department', 'Dependency'),
    'proposed_ocupation':fields.many2one('hr.job', 'Ocupation'),
    'proposed_parent_id':fields.many2one('hr.employee', 'Director'),
    'proposed_coach_id':fields.many2one('hr.employee', 'Coach'),
    'proposed_orderly_turn':fields.many2one('resource.calendar', 'Proposed work schedule'),
    'proposed_wage':fields.float('Wage', digits=(16, 2), readonly=True),
    'proposed_salary_scale_category':fields.selection((('1','1'),
                                                       ('2','2'),
                                                       ('3','3'),
                                                       ('4','4'),
                                                       ('5','5'),
                                                       ('6','6'),
                                                       ('7','7'),
                                                       ('8','8'),
                                                       ('9','9'),
                                                       ('10','10'),
                                                       ('11','11'),
                                                       ('12','12'),
                                                       ('13','13'),
                                                       ('14','14'),
                                                       ('15','15'),
                                                       ('16','16'),
                                                       ('17','17'),
                                                       ('18','18'),
                                                       ('19','19'),
                                                       ('20','20'),
                                                       ('21','21'),
                                                       ('22','22'),
                                                       ('23','23'),
                                                       ('24','24'),
                                                       ('25','25')), 'Salary Scale Category'),
    'proposed_salary_scale_level':fields.selection((('1','1'),
                                                    ('2','2'),
                                                    ('3','3'),
                                                    ('4','4'),
                                                    ('5','5'),
                                                    ('6','6')), 'Salary Scale Level'),
    'proposed_diff_scale':fields.float('Diff. Scale', digits=(16,2)),
    'proposed_total':fields.function(calc_proposed_total, string='Proposed Total', type='float'),
    'proposed_bonus':fields.float('Bonus', digits=(16, 2)),
    'proposed_end_new_contract':fields.date('End of contract'),
    'proposed_salary_cut':fields.float('Salary reduction', digits=(16, 2)),
    'proposed_misconduct':fields.text('Amonestacion'),
    'proposed_misconduct_level':fields.selection((('1','1'),
                                                    ('2','2'),
                                                    ('3','3')), 'Nivel falta cometida'),
    'proposed_transfer':fields.selection((
					 ('1','UAPA Santiago'), 
					 ('2','UAPA Santo Domingo'),
					 ('3','UAPA Nagua'),
					 ('4','CEGES Santo Domingo'),
                                         ('5','CEGES Santiago')), 'Transferencia entre recintos'), 
    #From here on the fields are for information only regarding salary compensation in case of employee leave.
    #This may change on another stage of the proyect.
    'days_severance':fields.integer('Days of severance',size=12),
    'severance':fields.float('Severance', digits=(16, 2)),
    'days_forewarning':fields.integer('Days of forewarning', size=12),
    'forewarning':fields.float('Forewarning', digits=(16,2)),
    'months_worked':fields.integer('Months worked', size=12),
    'monthly_salary':fields.float('Monthly Salary', digits=(16,2)),
    'christmas_salary':fields.float('Salario de navidad', digits=(16, 2)),
    'average_daily_salary':fields.float('Average daily salary', digits=(16, 2)),
    'vacations_days':fields.integer('Vacations days', size=12),
    'vacations':fields.float('Vacations', digits=(16,2)),
    'employee_benefits_total':fields.function(calc_employee_leave_total, string='Total Benefits', type='float'),
    'severance_days':fields.integer('Dias de cesantia', size=12),
    'severange_total':fields.float('Monto cesantia', digits=(16,2)),
    'days_worked':fields.integer('Dias trabajados', size=12),
    'total_worked':fields.float('Monto dias trabajados', digits=(16,2)),

    }
    
    _defaults = {'states':'draft'}
   
    def onchange_wage_by_contract(self, cr, uid, ids, contract_id, context=None):
	hr_cont_obj = self.pool.get('hr.contract')
	res = {}
	ids = contract_id
        for contract in self.read(cr, uid, ids, ['contract_id', 'wage'], context=context):
            res = contract
	
	return res
 
    def get_contract(self, cr, uid, employee, context=None):
	contract_obj = self.pool.get('hr.contract')
	clause_final =  [('employee_id', '=', employee.id)]
	contract_ids = contract_obj.search(cr, uid, clause_final, context=context)
	return contract_ids

    def onchange_wage(self, cr, uid, ids, employee_id, context=None):
        hr_contract_obj = self.pool.get('hr.contract')
        hr_obj = self.pool.get('hr.employee')

        if employee_id:
            hr_cont_id = hr_contract_obj.search(cr, uid, [('employee_id','=',employee_id)], order='id', context = None)

            emp_cont = hr_contract_obj.browse(cr, uid, hr_cont_id[-1], context=None)
            return {'value': {'proposed_wage':emp_cont.wage}}
        else:
            return {}	
    
    def onchange_petitioner(self, cr, uid, ids, origin_employee_id, context=None):
        """Fetchs the data of the employee that puts the request for the personnel action.
        
        Returns: Dictionary{'value':Dictionary{'field_that_shows':value_to_show}"""
        hr_obj = self.pool.get('hr.employee')	
        if origin_employee_id:
            employee = hr_obj.browse(cr, uid, origin_employee_id, context=None)
            return {'value':{'origin_address':employee.subsidiary_id.partner_id.street,
        'origin_department_id':employee.department_id.id,
        'origin_company_id':employee.subsidiary_id.id,
        'origin_state_id':employee.subsidiary_id.partner_id.state_id.id}}
        else:
            return {} 
        
    def onchange_petitionee(self, cr, uid, ids, employee_id, contract_id, context=None):
        """Fetchs the data of the employee who the petition is about.
        
        Returns: Dictionary{'value':Dictionary{'field_that_shows':values_to_show}"""
        hr_obj = self.pool.get('hr.employee')
        hr_contract_obj = self.pool.get('hr.contract')
	if context is None:
            context = {}
	
	#defaults
	res = {'value':{'contract_id': False }}
	if (not employee_id):
	    return res

	employee_obj = hr_obj.browse(cr, uid, employee_id, context=context)
	if not context.get('contract', False):
	    contract_ids = self.get_contract(cr, uid, employee_obj, context=context)
	else:
	    if contract_id:
	        contract_ids = [contract_id]
	    else:
		contract_ids = self.get_contract(cr, uid, employee_obj, context=context)

	if not contract_ids:
	    return res
	contract_record = hr_contract_obj.browse(cr, uid, contract_ids[0], context=context)

	if (not employee_id):
	    return res
	
	if employee_id:
	    emp = hr_obj.browse(cr, uid, employee_id, context=None)
	    hr_cont_id = hr_contract_obj.search(cr, uid, [('employee_id','=',employee_id)], order='id', context = None)
            try:
                emp_cont = hr_contract_obj.browse(cr, uid, hr_cont_id[-1], context=None)		
		res['value'].update({
	    			'actual_employee_code':emp.employee_code,
				'contract_id':emp_cont.id,
			        'actual_identification_id':emp.identification_id,
		                'actual_dependency':emp.department_id.id,
                                'actual_ocupation':emp.job_id.id,
                                'actual_salary_scale_category':emp.salary_scale_category,
		                'actual_salary_scale_level':emp.salary_scale_level,
		                'actual_orderly_turn':emp_cont.working_hours.id,
	                        'actual_wage':emp_cont.wage,
	                        'actual_diff_scale':emp_cont.diff_scale,
		                'actual_parent_id':emp.parent_id.id,
		                'actual_total': emp_cont.wage + emp_cont.diff_scale,
	                        'contract_id':contract_record and contract_record.id or False,
				'proposed_wage':emp_cont.wage})
		return res
            except:
                raise osv.except_osv('Error', 'The selected employee has no available contract.')
        else:
            return {}

    def onchange_contract_id(self, cr, uid, ids, employee_id=False, contract_id=False, context=None):
	if context is None:
	    context = {}
	hr_contract_obj = self.pool.get('hr.contract')
	res = {'value':{ }}
        emp_cont = hr_contract_obj.browse(cr, uid, contract_id, context=None)
	#context.update({'contract': True, 'actual_wage':emp_cont.wage, 'actual_diff_scale':emp_cont.diff_scale})
	res['value'].update({'actual_wage':emp_cont.wage, 'actual_diff_scale':emp_cont.diff_scale,
                             'actual_total': emp_cont.wage + emp_cont.diff_scale, 'proposed_wage':emp_cont.wage})
	if not contract_id:
	    res['value'].update({'struct_id': False})
	return res


    def action_approve(self, cr, uid, ids, context=None, **kwargs):
	self.write(cr, uid, ids, {'states':'approved'}, context=None)       
        #Variables that access the kwargs dictionary and search for the required parameter.
        effect_date = kwargs.get('effect_date')
        requested_id = kwargs.get('requested_id')
        requested_action = kwargs.get('requested_action')
        new_dependency = kwargs.get('new_dependency')
        new_job = kwargs.get('new_job')
        new_scale_categ = kwargs.get('new_scale_categ')
        new_scale_level = kwargs.get('new_scale_level')
        new_parent = kwargs.get('new_parent')
	new_transfer = kwargs.get('new_transfer')
        new_turn = kwargs.get('new_turn')
        new_wage = kwargs.get('new_wage')
        new_diff = kwargs.get('new_diff')
        bonus = kwargs.get('bonus')
	end_date = kwargs.get('end_date')
        end_new_contract = kwargs.get('end_new_contract')
        salary_cut = kwargs.get('salary_cut')

	ret = {}
	for contract in self.read(cr, uid, ids, ['contract_id'], context=context):
	    ret = contract
	#Used this for to get some fields that was added lately and don't appear
	pm = {}
        for record in self.read(cr, uid, ids, [], context=context):
            pm = record
		
	############
        #
        # Here on forward it handles personnel actions.
        # There is a if-else structure for handling each one of the actions.
        #
        ###########
        #This variables holds the objects we are going to be using in each action.
        hr_obj = self.pool.get('hr.employee')
        hr_cont_obj = self.pool.get('hr.contract')
        hr_cont_rate_obj = self.pool.get('hr.contract.rate')
        hr_holiday = self.pool.get('hr.holidays')
        hr_pay_obj = self.pool.get('hr.payslip')
        hr_payslip_obj = self.pool.get('hr.payslip.input')
        
        #A simple function to make sure that the action takes places today or if the effective date has passed already.
        def check_date(effect_date):
            effect_date = datetime.datetime.strptime(effect_date, '%Y-%m-%d')
            effect_date = datetime.date(effect_date.year, effect_date.month, effect_date.day)
            if effect_date < datetime.date.today():
                return True
            elif effect_date == datetime.date.today():
                return True
            else:
                return False
            
        #Id of the first contract of the employee.
        try:
            hr_cont_id = hr_cont_obj.search(cr, uid, [('employee_id','=', requested_id.id)], order='id', context=None)
            hr_cont_record = hr_cont_obj.browse(cr, uid, hr_cont_id[-1], context=None)
        except IndexError:
            raise osv.except_osv('Error', 'The selected employee has no available contract.')
   
 	
	#Action - Giving a bonus to the employee.
        if requested_action == '1':
            if check_date(effect_date):
		cr.execute("SELECT amount FROM hr_payslip_input WHERE contract_id IN ({}) ORDER BY id DESC LIMIT 1".format(hr_cont_id[-1]))
	        res = cr.fetchmany()
		if res[0][0] == bonus:
		   return True
		else:
		   hr_pay_id = hr_pay_obj.search(cr, uid, [('employee_id', '=', requested_id.id)], order='id', context=None)
		   hr_payslip_obj.create(cr, uid, {'contract_id':ret['contract_id'][0],
                                                'amount':bonus,
                                                'name':"Bonus pay for {0}.".format(requested_id.name_related.encode('utf-8')),
                                                'code':1,
                                                'payslip_id':hr_pay_id[0]}, context=None)
	    	   self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Probatory period dismissal
        elif requested_action == '2':
            if check_date(effect_date):
		hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'trial_date_end':effect_date}, context=None)
		cr.execute("select date_end from hr_contract where employee_id IN ({0}) ".format(requested_id.id))
                res = cr.fetchmany()
                if len(res) == 0:
                    hr_obj.write(cr, uid, requested_id.id, {'active':False}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Position changes.
        elif requested_action == '3':
            if check_date(effect_date):
                hr_obj.write(cr, uid, requested_id.id, {'department_id':new_dependency.id,
                                                        'job_id':new_job.id,'parent_id':new_parent.id},context=None)
		cr.execute("select id from account_analytic_account where department_id =  ({0}) ".format(new_dependency.id))
                res = cr.fetchmany()
                hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'working_hours':new_turn.id,
                                                            'job_id':new_job.id,
							    'analytic_account_id':res[0][0],
                                                            'wage':new_wage + new_diff}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Command line correction
        elif requested_action == '4':
            if check_date(effect_date):
                hr_obj.write(cr, uid, requested_id.id, {'parent_id':new_parent.id}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Actions - Decease and terminations unjustified. This is supposed to have benefits.
        elif requested_action == '5':
            if check_date(effect_date):
		hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'trial_date_end':effect_date}, context=None)
		cr.execute("select date_end from hr_contract where employee_id IN ({0}) ".format(requested_id.id))
                res = cr.fetchmany()
                if len(res) == 0:
		    hr_obj.write(cr, uid, requested_id.id, {'active':False}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
                #Todo Añadir aquellos valores que se le dan al empleado.
        #Actions - Justified termination. This is also supposed to have benefits.
        elif requested_action == '6':
            if check_date(effect_date):
		hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'trial_date_end':effect_date}, context=None)
		cr.execute("select date_end from hr_contract where employee_id IN ({0}) ".format(requested_id.id))
                res = cr.fetchmany()
                if len(res) == 0:
                    hr_obj.write(cr, uid, requested_id.id, {'active':False}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
	#Actions - Decease and terminations unjustified. This is supposed to have benefits.
	elif requested_action == '7':
            if check_date(effect_date):
		hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'trial_date_end':effect_date}, context=None)
		cr.execute("select date_end from hr_contract where employee_id IN ({0}) ".format(requested_id.id))
                res = cr.fetchmany()
                if len(res) == 0:
                    hr_obj.write(cr, uid, requested_id.id, {'active':False}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
	#Actions - Desativated. This is supposed to have benefits.
        elif requested_action == '8':
            if check_date(effect_date):
		hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'trial_date_end':effect_date}, context=None)
		cr.execute("select date_end from hr_contract where employee_id IN ({0}) ".format(requested_id.id))
                res = cr.fetchmany()
                if len(res) == 0:
                    hr_obj.write(cr, uid, requested_id.id, {'active':False}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Incorporation
        elif requested_action == '9':
            if check_date(effect_date):
                hr_obj.write(cr, uid, requested_id.id, {'active':True,
                                                     'on_vacation':False,
                                                     'on_licence':False}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Medical licence.
        elif requested_action == '10':
            if check_date(effect_date):
		cr.execute("SELECT date_to FROM hr_holidays WHERE employee_id IN ({0}) ORDER BY id DESC LIMIT 1".format(requested_id.id))
                res = cr.fetchmany()
                if len(res) == 0:
                   hr_obj.write(cr, uid, requested_id.id, {'on_licence':True}, context=None)
                   hr_holiday.create(cr, uid, {'state':'validate',
                                            'holiday_status_id':5,
                                            'employee_id':requested_id.id,
                                            'department_id':new_dependency.id,
                                            'holiday_type':'employee',
                                            'date_from':effect_date,
                                            'date_to':end_date,
                                            'number_of_days_temp':pm['days_of_vacations']}, context=None)
                   self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Maternity license.
        elif requested_action == '11':
            if check_date(effect_date):
		cr.execute("SELECT date_to FROM hr_holidays WHERE employee_id IN ({}) ORDER BY id DESC LIMIT 1".format(requested_id.id))
                res = cr.fetchmany()
                if len(res) == 0:
		   hr_obj.write(cr, uid, requested_id.id, {'on_licence':True}, context=None)
                   hr_holiday.create(cr, uid, {'state':'validate',
                                            'holiday_status_id':6,
                                            'employee_id':requested_id.id,
                                            'department_id':new_dependency.id,
                                            'holiday_type':'employee',
                                            'date_from':effect_date,
                                            'date_to':end_date,
                                            'number_of_days_temp':pm['days_of_vacations']}, context=None)
                   self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Promotion
        elif requested_action == '12':
            if check_date(effect_date):

                hr_obj.write(cr, uid, requested_id.id, {'department_id':new_dependency.id,
                                                        'job_id':new_job.id,
                                                        'parent_id':new_parent.id}, context=None)
                cr.execute("select id from account_analytic_account where department_id =  ({0}) ".format(new_dependency.id))
                res = cr.fetchmany()
		hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'working_hours':new_turn.id,
                                                            'job_id':new_job.id,
							    'analytic_account_id':res[0][0],
                                                            'wage':new_wage + new_diff}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Promotion and transference
        elif requested_action == '13':
            if check_date(effect_date):
                hr_obj.write(cr, uid, requested_id.id, {'department_id':new_dependency.id,
                                                        'job_id':new_job.id,
                                                        'salary_scale_category':new_scale_categ,
                                                        'salary_scale_level':new_scale_level}, context=None)
		cr.execute("select id from account_analytic_account where department_id =  ({0}) ".format(new_dependency.id))
                res = cr.fetchmany()
                hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'working_hours':new_turn.id,
							    'job_id':new_job.id,
                                                            'analytic_account_id':res[0][0],
                                                            'wage':new_wage + new_diff}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Wage changes
        elif requested_action == '14':
            if check_date(effect_date):		
		employee_id = requested_id.id
		hr_obj.write(cr, uid, requested_id.id, {'job_id':new_job.id,
                                                        'salary_scale_category':new_scale_categ,
                                                        'salary_scale_level':new_scale_level}, context=None)

                hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'wage':new_wage + new_diff}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Position reclasification - Changes all but department_id
        elif requested_action == '15':
            if check_date(effect_date):		
                hr_obj.write(cr, uid, requested_id.id, {'job_id':new_job.id,
                                                        'salary_scale_category':new_scale_categ,
                                                        'salary_scale_level':new_scale_level,
						        'parent_id':new_parent.id}, context=None)
                hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'working_hours':new_turn.id,
                                                            'wage':new_wage + new_diff}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Position reclasification with department changes
        elif requested_action == '16':
            if check_date(effect_date):
                hr_obj.write(cr, uid, requested_id.id, {'department_id':new_dependency.id,
							'job_id':new_job.id,
                                                        'salary_scale_category':new_scale_categ,
                                                        'salary_scale_level':new_scale_level,
							'parent_id':new_parent.id}, context=None)
		cr.execute("select id from account_analytic_account where department_id =  ({0}) ".format(new_dependency.id))
                res = cr.fetchmany()
                hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'job_id':new_job.id,
							    'analytic_account_id':res[0][0],
                                                            'working_hours':new_turn.id,
                                                            'wage':new_wage + new_diff}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Reintregation with the company. Old contract.
        elif requested_action == '17':
            if check_date(effect_date):
                hr_obj.write(cr, uid, requested_id.id, {'active':True,
                                                            'department_id':new_dependency.id,
                                                            'job_id':new_job.id,
                                                            'salary_scale_category':new_scale_categ,
                                                            'salary_scale_level':new_scale_level,
                                                            'parent_id':new_parent.id}, context=None)
                hr_cont_obj.write(cr, uid, ret['contract_id'][0], {
                                                             'date_start':effect_date,
							     'working_hours':new_turn.id,
                                                             'wage':new_wage  + new_diff}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Reintegration with a new contract.
        elif requested_action == '18':
            if check_date(effect_date):
                hr_obj.write(cr, uid, requested_id.id, {'active':True,
                                                            'department_id':new_dependency.id,
                                                            'job_id':new_job.id,
                                                            'salary_scale_category':new_scale_categ,
                                                            'salary_scale_level':new_scale_level,
                                                            'parent_id':new_parent.id}, context=None)
                hr_cont_obj.create(cr, uid, ret['contract_id'][0], {'working_hours':new_turn.id,
                                                'date_end':end_date,
                                                'employee_id':requested_id.id,
                                                'name':"Standard new contract for {0}.".format(requested_id.name_related),
                                                'date_start':effect_date,
                                                'date_end':end_new_contract,
                                                'schedule_pay':'monthly',
                                                'struct_id':1,
                                                'type_id':1,
                                                'wage':new_wage + new_diff}, context = None)                
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Disciplinary action.
        elif requested_action == '19':
            if check_date(effect_date):
		hr_obj.write(cr, uid, requested_id.id, {'proposed_misconduct': pm['proposed_misconduct'],
                                                        'proposed_misconduct_level': pm['proposed_misconduct_level']}, context=None)

                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #The hr employee must apply the deduction to the payslip of the sanctioned.
        #Action - Resignation
        elif requested_action == '20':
            if check_date(effect_date):
		hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'trial_date_end':effect_date}, context=None)
		cr.execute("select date_end from hr_contract where employee_id IN ({0}) ".format(requested_id.id))
                res = cr.fetchmany()
                if len(res) == 0:
                    hr_obj.write(cr, uid, requested_id.id, {'active':False}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - From temporary to permanent
        elif requested_action == '21':
            if check_date(effect_date):
                hr_cont_obj.write(cr, uid, ret['contract_id'][0], {'type_id':1, 'trial_date_end':effect_date, 'date_start':effect_date}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Transference
        elif requested_action == '22':
            if check_date(effect_date):
		idx = self.browse(cr, uid, ids)
                hr_obj.write(cr, uid, requested_id.id, {'transfer_to':idx[0].proposed_transfer[0]}, context=None)
                self.write(cr, uid, ids, {'states':'applied'},context=None)
        #Action - Vacations
        elif requested_action == '23':
	    cr.execute("SELECT date_to FROM hr_holidays WHERE employee_id IN ({}) ORDER BY id DESC LIMIT 1".format(requested_id.id))
            res = cr.fetchmany()
	    if len(res) == 0:
                if check_date(effect_date):
                    hr_obj.write(cr, uid, requested_id.id, {'on_vacation':True}, context=None)
		    vacation_id = hr_holiday.search(cr, uid, [])
                    hr_holiday.create(cr, uid, {'employee_id':requested_id.id,
                                                'department_id':new_dependency.id,
                                                'date_from':effect_date,
                                                'date_to':end_date,
						'name':'Solicitud de vacaciones',
                                                'holiday_status_id':7,
                                                'number_of_days_temp': pm['days_of_vacations'],  
                                                'state':'validate'}, context=None)
                    self.write(cr, uid, ids, {'states':'applied'},context=None)
		else:
		    raise osv.except_osv('Advertencia', 'Este empleado cuenta con vacaciones asignadas!')
	            return False
	return True        


    def action_confirm(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'states': 'confirmed'}, context=None)
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids,{'states': 'cancelled'}, context=None)
        return True

    def action_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'states': 'draft'}, context=None)
        return True
    
    def action_apply(self, cr, uid, ids, context=None):
        #self.run_personnel_actions(cr, uid, ids, context=None)
        self.write(cr, uid, ids, {'states': 'applied'}, context=None)
        return True


HrPersonnelAction()
