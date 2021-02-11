from simple_salesforce import Salesforce
import pandas as pd
import openpyxl as op
import collections

sf = Salesforce(username='patrick.carter@datadoghq.com',
                password='BostonBruins[]2',
                security_token='si4g3irPyxp8qzELb2akSuG4')

opp_data = sf.query_all(
    "select (select Id, Name, Owner.Name, CloseDate, Type, Finance_Type__c, Owner_Sales_Department__c, "
    "OrderOps_Assigned__r.Name, Account.Owner.Name, Org_Subteam__r.Owner__c, Contract_Type__c, CPQ_Quote_MRR__c, "
    "Growth_MRR__c, Change_in_Commit_MRR__c, CPQ_Start_Date__c, Org_Subteam__r.Billing_Plan_Type__c, "
    "Org_Subteam__r.Enterprise_Static_Baseline__c, Org_Subteam__r.Org_ID__c, Org_Subteam__r.Billing_Plan_Start_Date__c "
    "from Opportunities where CPQ_Start_Date__c = THIS_MONTH AND StageName = 'Closed Won') "
    "from Account where Id IN (select AccountId from Opportunity where CPQ_Start_Date__c = THIS_MONTH "
    "AND sbaa__ApprovalStatus__c IN ('Pending', 'Pre-Approved') AND StageName = 'Closed Won')")

opp_data_headers = [x for x in opp_data['records'][0]['Opportunities']['records'][0].keys()]
opp_data_dict = {header: [] for header in opp_data_headers}

for i in range(len(opp_data['records'])):
    for header in opp_data_headers:
        # print(opp_data['records'][i]['Opportunities']['records'][0][header])
        opp_data_dict[header].append(opp_data['records'][i]['Opportunities']['records'][0][header])
del opp_data_dict['attributes']
opp_df = pd.DataFrame(opp_data_dict)
opp_df2 = opp_df[['Owner', 'OrderOps_Assigned__r', 'Account', 'Org_Subteam__r']]
opp_df.drop(['Owner', 'OrderOps_Assigned__r', 'Account', 'Org_Subteam__r'], axis=1, inplace=True)


owner_dict = {'Opportunity_Owner': []}
org_owner = {'Org_Owner': []}
order_ops_assigned = {'Order_Ops_Assigned': []}
acct_owner = {'Account_Owner': []}
billing_plan = {'Billing_Plan': []}
baseline = {'Baseline': []}
org_id = {'Org_Id': []}
billing_start = {'Billing_Start_Date': []}
none_list= []

for item in opp_df2.columns:
    for i, r in opp_df2.iterrows():
        # print(r['OrderOps_Assigned__r'])
        if r[item] is None:
            # print(item)
            none_list.append((i, item, None))
        if isinstance(r[item], collections.OrderedDict):
            del r[item]['attributes']
            # print(r[item].values())`
            for j in r[item].values():
                if isinstance(j, collections.OrderedDict):
                    del j['attributes']
                    j['Account_Owner'] = j.pop('Name')
                    owner = j['Account_Owner']
                    acct_owner['Account_Owner'].append(owner)
            for k, v in r[item].items():
                if k == 'Name' and v in ('Denecia Mills-Jerome', 'Kelcia Ribeiro', 'Brian Deokaran', 'Patrick Carter', 'Kunal Mohan', 'Md Rahman'):
                    order_ops_assigned['Order_Ops_Assigned'].append(v)
                elif k == 'Name' and v not in ('Denecia Mills-Jerome', 'Kelcia Ribeiro', 'Brian Deokaran', 'Patrick Carter', 'Kunal Mohan', 'Md Rahman'):
                    owner_dict['Opportunity_Owner'].append(v)
                elif k == 'Owner__c':
                    org_owner['Org_Owner'].append(v)
                elif k == 'Billing_Plan_Type__c':
                    billing_plan['Billing_Plan'].append(v)
                elif k == 'Enterprise_Static_Baseline__c':
                    baseline['Baseline'].append(v)
                elif k == 'Org_ID__c':
                    org_id['Org_Id'].append(v)
                elif k == 'Billing_Plan_Start_Date__c':
                    billing_start['Billing_Start_Date'].append(v)


for tup in none_list:
    if tup[1] == 'OrderOps_Assigned__r':
        order_ops_assigned['Order_Ops_Assigned'].insert(tup[0], tup[2])

del opp_data_dict['Owner']
del opp_data_dict['Account']
del opp_data_dict['Org_Subteam__r']
del opp_data_dict['OrderOps_Assigned__r']
opp_data_dict.update(owner_dict)
opp_data_dict.update(order_ops_assigned)
opp_data_dict.update(acct_owner)
opp_data_dict.update(billing_plan)
opp_data_dict.update(baseline)
opp_data_dict.update(org_id)
opp_data_dict.update(billing_start)
opp_data_dict.update(org_owner)


headers = list(opp_data_dict.keys())
print([(x, len(opp_data_dict[x])) for x in headers])
opp_df = pd.DataFrame(opp_data_dict)
opp_df.to_csv('test3.csv')


#IF YOU ARE COPYING AND PASTING EXCEL DATA INTO WORKBOOK
# opp_data.drop(columns=['_', 'Opportunities', 'Opportunities.done', 'Opportunities.records', 'Opportunities.records.0',
#                        'Opportunities.records.0.Owner', 'Opportunities.records.0.OrderOps_Assigned__r',
#                        'Opportunities.records.0.Account',
#                        'Opportunities.records.0.Account.Owner', 'Opportunities.records.0.Org_Subteam__r'], inplace=True)
# opp_data.rename(columns={'Opportunities.records.0.Id': 'Opp_Id', 'Opportunities.records.0.Owner.Name': 'Opp_Owner',
#                          'Opportunities.records.0.CloseDate': 'Opp_Close_Date', 'Opportunities.records.0.Type': 'Type',
#                          'Opportunities.records.0.Finance_Type__c': 'Finance_Type',
#                          'Opportunities.records.0.Owner_Sales_Department__c': 'Opp_Owner_Dept',
#                          'Opportunities.records.0.OrderOps_Assigned__r.Name': 'OrderOps_Assigned',
#                          'Opportunities.records.0.Account.Owner.Name': 'Account_Owner',
#                          'Opportunities.records.0.Org_Subteam__r.Owner__c': 'Org_Owner',
#                          'Opportunities.records.0.Org_Subteam__r.Billing_Plan_Type__c': 'Org_Plan_Type',
#                          'Opportunities.records.0.Org_Subteam__r.Enterprise_Static_Baseline__c': 'Enterprise_Baseline',
#                          'Opportunities.records.0.Org_Subteam__r.Org_ID__c': 'OrgId',
#                          'Opportunities.records.0.Org_Subteam__r.Billing_Plan_Start_Date__c': 'Org_Start_Date',
#                          'Opportunities.records.0.Contract_Type__c': 'Contract_Type',
#                          'Opportunities.records.0.CPQ_Quote_MRR__c': 'Quote_MRR',
#                          'Opportunities.records.0.Growth_MRR__c': 'Growth_MRR',
#                          'Opportunities.records.0.Change_in_Commit_MRR__c': 'Change_In_Commit_MRR',
#                          'Opportunities.records.0.CPQ_Start_Date__c': 'CPQ_Start_Date',
#                          }, inplace=True)
# print(opp_data.columns)
# opp_data.to_csv('test_book.csv')
