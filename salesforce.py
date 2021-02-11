from simple_salesforce import Salesforce
import pandas as pd
import collections
import re
from collections import OrderedDict
from datetime import datetime
import numpy as np


sf = Salesforce(username='patrick.carter@datadoghq.com',
                password='BostonBruins[]2',
                security_token='si4g3irPyxp8qzELb2akSuG4')

sf_data_query = "SELECT Id, Name, sbaa__ApprovalStatus__c, Contract_Type__c, Finance_Type__c, OrderOps_Assigned__c FROM Opportunity " \
                "WHERE ((sbaa__ApprovalStatus__c in ('Pending', 'Pre-Approved') AND StageName = 'Closed Won' AND CPQ_Start_Date__c = THIS_MONTH AND OrderOps_Assigned__c = null) " \
                "OR (sbaa__ApprovalStatus__c in ('Pending', 'Pre-Approved') AND StageName = 'Closed Won' " \
                "AND CloseDate = THIS_MONTH AND Offer_Type__c = 'Drawdown' and CPQ_Quote_Type__c = 'Amendment' AND OrderOps_Assigned__c = null))"

queue_query = "SELECT Id, OrderOps_Assigned__r.Name, sbaa__ApprovalStatus__c from Opportunity " \
              "WHERE ((StageName = 'Closed Won' AND CPQ_Start_Date__c = THIS_MONTH AND sbaa__ApprovalStatus__c <> 'Approved') " \
              "OR (StageName = 'Closed Won' AND CloseDate = THIS_MONTH AND Offer_Type__c = 'Drawdown' AND CPQ_Quote_Type__c = 'Amendment'))"

autoconvert_query = "select Id, Name, Billed_Org_ID__c, sbaa__ApprovalStatus__c, CloseDate, CPQ_Start_Date__c, Contract_Type__c, Offer_Type__c, SBQQ__PrimaryQuote__r.Name, MRR__c, OrderOps_Assigned__c from Opportunity " \
                    "where CPQ_Start_Date__c = THIS_MONTH and sbaa__ApprovalStatus__c IN ('Pre-Approved', 'Pending') " \
                    "and Contract_Type__c in ('In-App Commit', 'Pay-as-you-go')"

clickthrough_query = "SELECT Org_Subteam__r.Name, MAX(Org_ID__c), MIN(Signup_Date__c), MAX(Plan_Type__c), MAX(Plan_Duration__c) FROM Click_Through_Contract__c " \
                     "WHERE Signup_Date__c = THIS_MONTH GROUP BY Org_Subteam__r.Name"

quote_query = "SELECT SBQQ__Quote__r.Name, Product_Display_Name__c, Overage_Option__c FROM SBQQ__QuoteLine__c " \
              "WHERE SBQQ__Quote__r.Start_Date_OrderForm__c = THIS_MONTH AND SBQQ__Quote__r.SBQQ__Opportunity2__r.StageName = 'Closed Won' " \
              "AND SBQQ__Product__r.Name in ('Datadog Pay-as-you-go Plan', 'Datadog Committed Plan') and SBQQ__Quote__r.SBQQ__Opportunity2__r.sbaa__ApprovalStatus__c <> 'Approved'"

quote_query2 = "SELECT SBQQ__Quote__r.SBQQ__Opportunity2__r.Org_Subteam__c, MAX(SBQQ__Quote__r.SBQQ__Opportunity2__r.Billed_Org_ID__c), SUM(SBQQ__Quantity__c), SUM(Sales_Price__c) FROM SBQQ__QuoteLine__c " \
               "WHERE SBQQ__Quote__r.Start_Date_OrderForm__c = THIS_MONTH AND SBQQ__Quote__r.SBQQ__Opportunity2__r.StageName = 'Closed Won' " \
               "AND Sales_Price__c <> null and SBQQ__Quote__r.SBQQ__Opportunity2__r.Contract_Type__c IN ('In-App Commit', 'Pay-as-you-go') AND SBQQ__Quote__r.SBQQ__Primary__c = true GROUP BY SBQQ__Quote__r.SBQQ__Opportunity2__r.Org_Subteam__c"

clickthrough_query2 = "SELECT Org_Subteam__c, MAX(Org_ID__c), SUM(Quantity__c), SUM(Price__c) FROM Click_Through_Contract__c " \
                      "WHERE Signup_Date__c = THIS_MONTH and Plan_Type__c IN ('Committed', 'Pay As You Go') GROUP BY Org_Subteam__c"

quote_id_query = "SELECT Id, Name FROM SBQQ__Quote__c WHERE SBQQ__Opportunity2__r.StageName = 'Closed Won' " \
                 "AND Start_Date_OrderForm__c = THIS_MONTH AND SBQQ__Opportunity2__r.sbaa__ApprovalStatus__c <> 'Approved'"


def assign_opp_not_assigned(rep_list, temp_list):
    # Display the Queue
    display_current_queue()
    # Try to pull Unassigned Opps from SF.  Return nothing if no records.
    try:
        sf_df = get_sf_data()
    except KeyError:
        print('There are no records that match your query')
        return None
    # Split the data into Pending and Pre-Approved
    preapproved_df, pending_df = split_sf_data(sf_df)
    ans = input(
        f'There are a total of {len(sf_df)} records to assign. {len(preapproved_df)} are Pre-Approved and {len(pending_df)} are Pending.  Would you like to proceed? (y/n): ')
    # Redo the input piece to separately ask who to assign to Pending/Pre-Approved Opps
    if ans.lower() == 'y':
        while True:
            reps_assigned_pending = input(
                'List the people to be assigned Pending Opportunities separated by a comma.  If everyone should be assigned, please enter \'All\': ')
            input_list = re.split(r',? ', reps_assigned_pending, len(rep_list))
            if reps_assigned_pending.lower() == 'all':
                secondary_approver_queue = collections.deque([x[0] for x in rep_list if x[1] == 'Level 3'])
                rep_queue = collections.deque([x[0] for x in rep_list])
                temp_queue = collections.deque(temp_list)
                break
            else:
                lst_rep = [list(x) for x in rep_list]
                for name in lst_rep:
                    for i in input_list:
                        if i in name[2]:
                            name.append(True)
                    if len(name) != 4:
                        name.append(False)
                secondary_approver_queue = collections.deque(
                    [x[0] for x in lst_rep if (x[1] == 'Level 3') and x[3] is True])
                rep_queue = collections.deque([x[0] for x in lst_rep if x[3] is True])
                temp_queue = collections.deque(temp_list)
                break
        for index, row in pending_df.iterrows():
            if row['Contract_Type__c'] in ('In-App Commit', 'Pay-as-you-go'):
                row['Assigned Rep'] = temp_queue[0]
                temp_queue.rotate(1)
            else:
                row['Assigned Rep'] = rep_queue[0]
                rep_queue.rotate(1)
        while True:
            reps_assigned_pending = input(
                'List the people to be assigned Pre-Approved Opportunities separated by a comma.  If everyone should be assigned, please enter \'All\': ')
            input_list = re.split(r',? ', reps_assigned_pending, len(rep_list))
            if reps_assigned_pending.lower() == 'all':
                secondary_approver_queue = collections.deque([x[0] for x in rep_list if x[1] == 'Level 3'])
                break
            else:
                lst_rep = [list(x) for x in rep_list]
                for name in lst_rep:
                    for i in input_list:
                        if i in name[2]:
                            name.append(True)
                    if len(name) != 4:
                        name.append(False)
                secondary_approver_queue = collections.deque(
                    [x[0] for x in lst_rep if (x[1] == 'Level 3') and x[3] is True])
                break
        for index, row in preapproved_df.iterrows():
            try:
                row['Assigned Rep'] = secondary_approver_queue[0]
                secondary_approver_queue.rotate(1)
            except IndexError:
                continue
    else:
        return None
    merged_df = join_df(preapproved_df, pending_df)
    merged_df.to_csv('combined_data.csv')
    id = list(merged_df['Id'])
    assigned_rep = list(merged_df['Assigned Rep'])
    pairs = list(zip(id, assigned_rep))
    count = 0
    for i, v in pairs:
        if v:
            count += 1
            print(f'****** Updating Record {i} ....... {((count / len(sf_df)) * 100):.2f}% complete ******')
            sf.Opportunity.update(str(i), {'OrderOps_Assigned__c': str(v)})
    else:
        return None


def get_sf_data():
    sf_data = sf.query_all(sf_data_query)
    sf_df = pd.DataFrame(sf_data['records']).drop(columns='attributes')
    sf_df.rename(columns={'OrderOps_Assigned__c': 'Assigned Rep'}, inplace=True)
    return sf_df


def split_sf_data(df):
    preapproved_df = df[df['sbaa__ApprovalStatus__c'] == 'Pre-Approved']
    pending_df = df[df['sbaa__ApprovalStatus__c'] == 'Pending']
    return preapproved_df, pending_df


def display_current_queue():
    queue = sf.query_all(queue_query)
    queue_df = pd.DataFrame(queue['records']).drop(columns='attributes')

    for i, r in queue_df.iterrows():
        if isinstance(r['OrderOps_Assigned__r'], collections.OrderedDict):
            del r['OrderOps_Assigned__r']['attributes']
            r['OrderOps_Assigned__r'] = list(r['OrderOps_Assigned__r'].values())[0]
        else:
            r['OrderOps_Assigned__r'] = 'Not Assigned'
    queue_df['Pending'] = queue_df['sbaa__ApprovalStatus__c'].apply(lambda x: 1 if x == 'Pending' else 0)
    queue_df['Pre-Approved'] = queue_df['sbaa__ApprovalStatus__c'].apply(lambda x: 1 if x == 'Pre-Approved' else 0)
    group_queue_df = queue_df.groupby(['OrderOps_Assigned__r']).sum()
    print('Below is the current queue:'
          '\n*********************************************')
    print(group_queue_df)
    print('*********************************************')


def join_df(df1, df2):
    frames = [df1, df2]
    return pd.concat(frames)


def approve_autoconverts():
    try:
        autoconverts = sf.query_all(autoconvert_query)
        clickthrough = sf.query_all(clickthrough_query)
        quotes = sf.query_all(quote_query)
        df1 = pd.DataFrame(autoconverts['records']).drop(columns='attributes')
        primary_quote = []
        for i, r in df1.iterrows():
            if isinstance(r['SBQQ__PrimaryQuote__r'], collections.OrderedDict):
                del r['SBQQ__PrimaryQuote__r']['attributes']
                primary_quote.append(list(r['SBQQ__PrimaryQuote__r'].values())[0])
        df1['SBQQ__PrimaryQuote__r'] = primary_quote
        df2 = pd.DataFrame(clickthrough['records']).drop(columns='attributes')
        df3 = pd.DataFrame(quotes['records']).drop(columns='attributes')
        quote = []
        for i, r in df3.iterrows():
            if isinstance(r['SBQQ__Quote__r'], collections.OrderedDict):
                del r['SBQQ__Quote__r']['attributes']
                quote.append(list(r['SBQQ__Quote__r'].values())[0])
        df3['SBQQ__Quote__r'] = quote
        df3.rename(columns={'SBQQ__Quote__r': 'Quote'}, inplace=True)
    except KeyError:
        print('There are no Autoconverts')
        return None
    quote_df = get_quote_data(clickthrough_query2, quote_query2)
    df4 = merge_df(df1, df2)
    df4.rename(columns={'SBQQ__PrimaryQuote__r': 'Quote'}, inplace=True)
    df5 = df4.merge(df3, how='inner', on='Quote')
    final_df = df5.merge(quote_df, how='inner', on='Org_ID')
    checked_df = check_values(final_df)
    fixed_df, counter = fix_rejected_opp(checked_df)
    id, value, error_name, approved_name = add_to_df(fixed_df)
    approved_df = pd.DataFrame(approved_name)
    error_df = pd.DataFrame(error_name)
    approved_df.to_csv('approved_autoconverts.csv')
    error_df.to_csv('rejected_autoconverts.csv')
    pairs = list(zip(id, value))
    ans = input(
        f"There are {len(approved_name)} Autoconverts to approve.  {len(error_name)} {'has' if len(error_name) == 1 else 'have'} {'an error' if len(error_name) == 1 else 'errors'} and "
        f"{counter if counter != 0 else 'No'} {'fix' if counter == 1 else 'fixes'} {'was' if counter == 1 else 'were'} made. Would you like to proceed? (y/n): ")
    if ans.lower() == 'y':
        count = 0
        for i, v in pairs:
            count += 1
            print(f'****** Approving Record {i} ....... {((count / len(pairs)) * 100):.2f}% complete ******')
            sf.Opportunity.update(str(i), {'sbaa__ApprovalStatus__c': str(v)})
    else:
        try:
            print(error_df[['Name_x', 'Org_ID']])
        except KeyError:
            print('All Autoconverts are accurate')
        return None


def merge_df(df1, df2):
    df1.rename(columns={'Billed_Org_ID__c': 'Org_ID'}, inplace=True)
    df2.rename(columns={'expr0': 'Org_ID', 'expr1': 'Signup_Date', 'expr2': 'Plan_Type', 'expr3': 'Plan Duration'},
               inplace=True)
    df3 = df1.merge(df2, how='inner', on='Org_ID')
    df3['Signup_Date'] = pd.to_datetime(df3['Signup_Date'])
    df3['Signup_Date'] = df3['Signup_Date'].dt.tz_convert('US/Eastern')
    df3['Signup_Date'] = df3['Signup_Date'].apply(lambda x: x.strftime('%Y-%m-%d'))

    return df3


def check_values(df):
    df['Dates_Match'] = np.where(
        (df['Signup_Date'] == df['CloseDate']) & (df['Signup_Date'] == df['CPQ_Start_Date__c']), True, False)
    df['Plans_Match'] = np.where(
        ((df['Plan_Type'] == 'Pay As You Go') & (df['Contract_Type__c'] == 'Pay-as-you-go')) & (
                df['Product_Display_Name__c'] == 'Datadog Pay-as-you-go Plan') |
        ((df['Plan_Type'] == 'Committed') & (df['Contract_Type__c'] == 'In-App Commit') & (
                df['Product_Display_Name__c'] == 'Datadog Committed Plan')), True, False)
    df['Duration_Match'] = np.where(
        ((df['Plan Duration'] == 'Monthly') & (df['Offer_Type__c'] == 'Month-to-Month')) |
        ((df['Plan Duration'] == 'Annually') & (df['Offer_Type__c'] == 'Multi-Month Commitment')), True, False)
    df['OD_Match'] = np.where(
        (df['Plan_Type'] == 'Pay As You Go') & (df['Overage_Option__c'] == 'Monthly') |
        (df['Plan_Type'] == 'Committed') & (df['Overage_Option__c'] == 'Hourly'), True, False)
    df['Product_Match'] = np.where(
        ((df['Product_Count_CC'] == df['Product_Count_Quote']) & (df['Plan_Type'] == 'Committed')) | (
                df['Plan_Type'] == 'Pay As You Go'), True, False)
    df['Price_Match'] = np.where(((df['Total_Price_CC'] == df['Total_Price_Quote']) & (
            df['Plan_Type'] == 'Committed') | (df['Plan_Type'] == 'Pay As You Go')), True, False)
    df['Full_Match'] = np.where(
        ((df['Dates_Match'] == True)
         & (df['Plans_Match'] == True)
         & (df['Duration_Match'] == True)
         & (df['OD_Match'] == True)
         & (df['Product_Match'] == True)
         & (df['Price_Match'] == True)), True, False)
    return df


def get_quote_data(query1, query2):
    cc = sf.query_all(query1)
    quote = sf.query_all(query2)
    cc_df = pd.DataFrame(cc['records']).drop(columns='attributes')
    quote_df = pd.DataFrame(quote['records']).drop(columns='attributes')
    cc_df.rename(columns={'expr0': 'Org_ID', 'expr1': 'Product_Count_CC', 'expr2': 'Total_Price_CC'}, inplace=True)
    cc_df['Total_Price_CC'] = cc_df['Total_Price_CC'].round(2)
    quote_df.rename(columns={'expr0': 'Org_ID', 'expr1': 'Product_Count_Quote', 'expr2': 'Total_Price_Quote'},
                    inplace=True)
    quote_df['Total_Price_Quote'] = quote_df['Total_Price_Quote'].round(2)
    merge_df = quote_df.merge(cc_df, how='inner', on='Org_ID').drop(columns=['Org_Subteam__c_x', 'Org_Subteam__c_y'])
    return merge_df


def fix_rejected_opp(df):
    id_df = sf.query_all(quote_id_query)
    id = pd.DataFrame(id_df['records']).drop(columns='attributes')
    id.rename(columns={'Name': 'Quote'}, inplace=True)
    df = df.merge(id, how='inner', on='Quote')
    df['Error_Reason'] = None
    error_list = []
    # import pdb;
    # pdb.set_trace()
    # df.to_csv('fix_df.csv')
    counter = 0
    for i, r in df.iterrows():
        # change_owner(r)
        if r['Dates_Match'] is False:
            counter += 1
            if r['Signup_Date'] != r['CloseDate']:
                df.iloc[i, df.columns.get_loc('CloseDate')] = r['Signup_Date']
                print(f'****** Fixing {r["Id_x"]}.  Adjusting Opportunity Close Date  ******')
                sf.Opportunity.update(str(r['Id_x']), {'CloseDate': str(r['Signup_Date'])})
                error_list.append((i, 'Fixed'))
            if r['Signup_Date'] != r['CPQ_Start_Date__c']:
                df.iloc[i, df.columns.get_loc('CPQ_Start_Date__c')] = r['Signup_Date']
                print(f'****** Fixing {r["Id_y"]}.  Adjusting CPQ Start Date  ******')
                sf.SBQQ__Quote__c.update(str(r['Id_y']), {'Start_Date_OrderForm__c': str(r['Signup_Date'])})
                error_list.append((i, 'Fixed'))
        if r['Plans_Match'] is False:
            counter += 1
            if r['Plan_Type'] == 'Committed' and r['Contract_Type__c'] != 'In-App Commit':
                df.iloc[i, df.columns.get_loc('Contract_Type__c')] = 'In-App Commit'
                print(f'****** Fixing {r["Id_x"]}.  Adjusting Contract Type.  ******')
                sf.Opportunity.update(str(r['Id_x']), {'Contract_Type__c': 'In-App Commit'})
                error_list.append((i, 'Fixed'))
            if r['Plan_Type'] == 'Pay As You Go' and r['Contract_Type__c'] != 'Pay-as-you-go':
                df.iloc[i, df.columns.get_loc('Contract_Type__c')] = 'Pay-as-you-go'
                print(f'****** Fixing {r["Id_x"]}.  Adjusting Contract Type.  ******')
                sf.Opportunity.update(str(r['Id_x']), {'Contract_Type__c': 'Pay-as-you-go'})
                error_list.append((i, 'Fixed'))
            else:
                df.iloc[i, df.columns.get_loc('Error_Reason')] = 'Need to Adjust CPQ Bundle - Quote Bundle Type'
        if r['Duration_Match'] is False:
            counter += 1
            # import pdb;
            # pdb.set_trace()
            if r['Plan Duration'] == 'Monthly' and r['Offer_Type__c'] != 'Month-to-Month':
                df.iloc[i, df.columns.get_loc('Offer_Type__c')] = 'Month-to-Month'
                print(f'****** Fixing {r["Id_y"]}.  Adjusting CPQ Contract Duration  ******')
                sf.SBQQ__Quote__c.update(str(r['Id_y']), {'Offer_Type__c': 'Month-to-Month'})
                print(f'****** Fixing {r["Id_x"]}.  Adjusting Opportunity Contract Duration  ******')
                sf.Opportunity.update(str(r['Id_x']), {'Offer_Type__c': 'Month-to-Month'})
                error_list.append((i, 'Fixed'))
            if r['Plan Duration'] == 'Annually' and r['Offer_Type__c'] != 'Multi-Month Commitment':
                df.iloc[i, df.columns.get_loc('Offer_Type__c')] = 'Multi-Month Commitment'
                print(f'****** Fixing {r["Id_y"]}.  Adjusting CPQ Contract Duration  ******')
                sf.SBQQ__Quote__c.update(str(r['Id_y']), {'Offer_Type__c': 'Multi-Month Commitment'})
                print(f'****** Fixing {r["Id_x"]}.  Adjusting Opportunity Contract Duration  ******')
                sf.Opportunity.update(str(r['Id_x']), {'Offer_Type__c': 'Multi-Month Commitment'})
                error_list.append((i, 'Fixed'))
        if r['OD_Match'] is False:
            error_list.append((i, 'Need to Adjust CPQ Bundle - On Demand'))
        if r['Product_Match'] is False:
            error_list.append((i, 'Need to Adjust CPQ Bundle - Products'))
        if r['Price_Match'] is False:
            error_list.append((i, 'Need to Adjust CPQ Bundle - Pricing'))
    for i, error in error_list:
        df.iloc[i, df.columns.get_loc('Error_Reason')] = error
    # import pdb;
    # pdb.set_trace()
    final_check = check_values(df)
    return final_check, counter


def add_to_df(df):
    id = []
    value = []
    error_name = []
    approved_name = []
    for i, r in df.iterrows():
        if r['Full_Match']:
            id.append(r['Id_x'])
            value.append('Approved')
            approved_name.append(r)
        else:
            error_name.append(r)
    return id, value, error_name, approved_name

def change_owner_to_pat(row):
    if row['OrderOps_Assigned__c'] != '0050e000007N0N4AAK':
        print(f'****** Fixing {row["Id_x"]}.  Adjusting Opportunity Owner  ******')
        sf.Opportunity.update(str(row['Id_x']), {'OrderOps_Assigned__c': '0050e000007N0N4AAK'})
        row['OrderOps_Assigned__c'] = '0050e000007N0N4AAK'
