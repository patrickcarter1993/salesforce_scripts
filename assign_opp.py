from salesforce import assign_opp_not_assigned
from simple_salesforce import Salesforce
import pandas as pd

sf = Salesforce(username='enter_username_here',
                password='enter_password_here',
                security_token='enter_securitytoken_here')

rep_data = sf.query_all("SELECT Name, X18_Char_User_ID__c, OrderOps_Level__c FROM User "
                        "WHERE (Title = 'Order Operations Analyst' OR Title = 'Order Operation Analyst-EMEA' OR Name "
                        "= 'Patrick Carter') AND IsActive = True")

temp_data = sf.query_all("SELECT Name, X18_Char_User_ID__c, OrderOps_Level__c FROM User "
                         "WHERE Title = 'Order Operation Temp' AND IsActive = True")

rep_df = pd.DataFrame(rep_data['records']).drop(columns='attributes')
temp_df = pd.DataFrame(temp_data['records']).drop(columns='attributes')
list_of_reps = list(zip(list(rep_df['X18_Char_User_ID__c']), list(rep_df['OrderOps_Level__c']), list(rep_df['Name'])))
list_of_temps = list(temp_df['X18_Char_User_ID__c'])


# print(list_of_temps)
# print(list_of_reps)

assign_opp_not_assigned(list_of_reps, list_of_temps)
