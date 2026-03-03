import os
import certifi
import snowflake.connector as connector
import pandas as pd
import base64
import configparser
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Email, Attachment, FileContent, FileName,
    FileType, Disposition, Personalization
)
import datetime
import json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from io import StringIO
from google.cloud import secretmanager


# ==================== LOGGING SETUP ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
os.environ['SSL_CERT_FILE'] = certifi.where()
config = configparser.ConfigParser()
config.read("config.ini")


def access_secret(project_id: str, secret_id: str, version_id: str = "latest") -> str:
    """
    Access the value of a secret from Google Cloud Secret Manager.

    Args:
        project_id: GCP project ID where the secret is stored.
        secret_id: The name/ID of the secret.
        version_id: The version to access (default "latest").

    Returns:
        The secret data as a string.
    """
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    secret_value = response.payload.data.decode("UTF-8")
    return secret_value


PROJECT_ID = "941299108492"
SECRET_ID = "data-platform-sendgrid"
VERSION = "latest"

API_KEY = access_secret(PROJECT_ID, SECRET_ID, VERSION)

try:
    settings = config["SETTINGS"]
except KeyError:
    settings = {}
    logger.warning("SETTINGS section not found in config.ini")

FROM_EMAIL = settings.get("FROM_EMAIL")
TO_EMAILS = [email.strip() for email in settings.get("TO_EMAILS", "").split(",") if email.strip()]
CC_EMAILS = [email.strip() for email in settings.get("CC_EMAILS", "").split(",") if email.strip()]
BCC_EMAILS = [email.strip() for email in settings.get("BCC_EMAILS", "").split(",") if email.strip()]
SNOWFLAKE_CREDS_FILE = settings.get("SNOWFLAKE_CREDS_FILE", "/home/ubuntu/BI/cfspl_snf_creds_admin_v1.json")
FILENAME = settings.get("FILENAME")
SUBJECT = settings.get("SUBJECT")
HTML_CONTENT = settings.get("HTML_CONTENT")

# ==================== EMBEDDED SQL QUERY ====================
QUERY = """
select * from 
(Select DEALER_CODE,COMPANY_NAME as Dealer_Name,Unnati_credit_limit AS Limit_Sanctioned,ROI,LTV,
        DATE_OF_INCORPORATION_AS_PER_REGISTRATION_PROOF as DATE_OF_INCORPORATION,BUSSINESS_REG_NUMBER_ON_PANEL as BUSSINESS_REG_NUMBER,BUSSINESS_REG_TYPE,ENLISTED_DATE as Unnati_Enlistment_Date,ADDRESS as ADDRESS_Dealership,
PINCODE as PINCODE_Dealership,CITY as CITY_Dealership,STATE as STATE_Dealership,DEALERSHIP_PAN,ENTITY_CONSTITUTION,
PROPRIETOR_1 as Applicant_NAME,GUARDIAN_NAME as Applicant_FATHER_NAME,
PRIMARY_NUMBER as Applicant_CONTACT_NUMBER,DATE_OF_BIRTH as Applicant_DOB,EMAIL as Applicant_EMAIL,GENDER as Applicant_GENDER, PAN_PROPRIETOR_1 as Applicant_PAN_NUMBER,PER_RESIDENCE_ADDRESS Applicant_PERMANENT_ADDRESS,
PER_ADDRESS_PINCODE Applicant_PERMANENT_ADDRESS_PINCODE,PER_ADDRESS_CITY Applicant_PERMANENT_ADDRESS_City ,
STATE Applicant_PERMANENT_ADDRESS_STATE,CURRENT_ADDRESS Applicant_Present_ADDRESS,CURRENT_ADDRESS_PINCODE Applicant_Present_ADDRESS_PINCODE,CITY Applicant_Present_ADDRESS_City,STATE Applicant_Present_ADDRESS_STATE,

COAPP_NAME CO_APP_NAME,FATHER_HUSBAND_NAME CO_APP_FATHER_NAME,COAPP_CONTACT CO_APP_CONTACT_NUMBER,COPP_DOB CO_APP_DOB,
COAPP_EMAILID CO_APP_EMAIL,CO_APP_GENDER COAPP_GENDER,COAPP_PANCARD CO_APP_PAN_NUMBER,CURRENT_ADDRESS_COAPP CO_APP_PRESENT_ADDRESS,CURRENT_PINCODE_COAPP CO_APP_PRESENT_ADDRESS_PINCODE,CURRENT_CITY_COAPP CO_APP_PRESENT_ADDRESS_City,
CURRENT_STATE_COAPP CO_APP_PRESENT_ADDRESS_STATE,PERMANENT_ADDRESS_COAPP CO_APP_PERMANENT_ADDRESS,PERMANENT_PINCODE_COAPP CO_APP_PERMANENT_ADDRESS_PINCODE,PERMANENT_CITY_COAPP CO_APP_PERMANENT_ADDRESS_City,PERMANENT_STATE_COAPP CO_APP_PERMANENT_ADDRESS_STATE
from
(select *
from CFSPL_CF_DCF_DB.GSHEET.UNNATI_NEW_DEALER_ONBOARDING
where ENLISTED_DATE is not null) onb
left join 
(SELECT APPLICANT_CODE as APP_CODE,APPLICANT_ID,NAME,EMAIL,PRIMARY_NUMBER,GENDER,APPLICANT_CODE,SOURCE,STATUS,
       INTREST_RATE,INTEREST_RATE_SECOND,
       (credit_limit + upliftment_limit) as Unnati_credit_limit,
       case when advance_payment is not null then  100-ADVANCE_PAYMENT else null end AS LTV,
       intrest_rate as ROI,ADDRESS,ENTITY_CONSTITUTION,ALTERNATE_EMAIL,COMPANY_NAME,DEALERSHIP_PAN,
       REGION_NAME,SPOUSE_NAME,SPOUSE_NUMBER,OFFICE_ADDRESS,OFFICE_TYPE,PER_RESIDENCE_ADDRESS,PER_ADDRESS_PINCODE,
       PER_RESIDENCE_ADDRESS_TYPE,CURRENT_ADDRESS,CURRENT_ADDRESS_TYPE,CURRENT_ADDRESS_PINCODE,
       PERMANENT_RESIDENCE_ADDRESS_PROOF,CURRENT_RESIDENCE_ADDRESS_PROOF,OFFICE_ADDRESS_PROOF_TYPE,
       PERMANENT_RESIDENCE_ADDRESS_TYPE,AGREEMENT_SIGNING_DATE,PROPRIETOR_1,PAN_PROPRIETOR_1,OFFICE_PINCODE,
       OFFICE_LOCATION,DATE_OF_BIRTH,GUARDIAN_NAME,MARITAL_STATUS,CITY,STATE,PINCODE,GUARDIAN_NUMBER,PER_ADDRESS_CITY
from  "CFSPL_NBFC_DB"."DF_PROD_DF_PROD"."FE_APPLICANTS"
where source not in ('Exempted dealer')
     AND status in ('enlisted')) as app
on onb.DEALER_CODE=app.APP_CODE
left join 

(select fe.applicant_code,COAPP_NAME,FATHER_HUSBAND_NAME ,COAPP_CONTACT ,COPP_DOB ,COAPP_EMAILID ,
       CO_APP_GENDER ,COAPP_PANCARD ,CURRENT_ADDRESS_COAPP ,CURRENT_PINCODE_COAPP ,CURRENT_CITY_COAPP ,
       CURRENT_STATE_COAPP ,PERMANENT_ADDRESS_COAPP ,PERMANENT_PINCODE_COAPP ,PERMANENT_CITY_COAPP ,PERMANENT_STATE_COAPP 
from 
(
  SELECT 
    applicant_code, 
    applicant_id 
  FROM "CFSPL_NBFC_DB"."DF_PROD_DF_PROD"."FE_APPLICANTS" 
  WHERE status = 'enlisted' AND credit_limit > 0 AND source NOT IN ('Exempted dealer')
) fe
left join 
(Select co_applicant_id, applicant_id, 
name as coapp_name, 
gender as co_app_gender,
pancard_no as coapp_pancard, 
contact_no as coapp_contact,
address_proof_id as COAPP_aadhar, 
email_id as coapp_emailid,
spouse_name as co_app_spouse_name,
date_of_birth as copp_DOB,
mother_name as coapp_mother, 
guardian_name as father_husband_name,
occupation_type as copp_occupation_type,
row_number() over(partition by applicant_id order by created_at desc ) as rank from "CFSPL_NBFC_DB"."EWS_CE_PROD"."FE_CO_APPLICANT" qualify rank = 1) co_app1
on fe.applicant_id =co_app1.applicant_id
left join
(Select reference_id,
max(case when address_type in ('PERMANENT') then address end) as permanent_Address_coapp, 
max(case when address_type in ('PERMANENT') then CITY end) as permanent_CITY_coapp,
max(case when address_type in ('PERMANENT') then STATE end) as permanent_STATE_coapp,
max(case when address_type in ('PERMANENT') then PINCODE end) as permanent_PINCODE_coapp,
max(case when address_type in ('CURRENT') then address end)  as current_address_coapp,
max(case when address_type in ('CURRENT') then CITY end)  as current_CITY_coapp,
max(case when address_type in ('CURRENT') then STATE end)  as current_STATE_coapp,
max(case when address_type in ('CURRENT') then PINCODE end)  as current_PINCODE_coapp,
from "CFSPL_NBFC_DB"."EWS_CE_PROD"."APPLICANT_ADDRESS" where SOURCE in ('CO-APPLICANT') group by 1) co_add
on co_app1.co_applicant_id=co_add.reference_id ) coapp
on onb.DEALER_CODE=coapp.applicant_code)
WHERE TRY_TO_DATE(UNNATI_ENLISTMENT_DATE, 'DD/MM/YYYY') <= CURRENT_DATE() - INTERVAL '1 DAY'
"""

# ==================== SNOWFLAKE FUNCTIONS ====================
def get_snowflake_connection(role=None, wh=None, db=None, schema=None):
    """
    Establish connection to Snowflake
    Args:
        role (str): Snowflake role
        wh (str): Snowflake warehouse
        db (str): Snowflake database
        schema (str): Snowflake schema
    Returns:
        connection: Snowflake connection object
    """
    try:
        creds_file = SNOWFLAKE_CREDS_FILE
        
        if os.path.exists(creds_file):
            logger.info(f"Loading Snowflake credentials from {creds_file}")
            with open(creds_file, 'r') as f:
                sf_account = json.load(f)
        else:
            logger.info("Loading Snowflake credentials from environment variable")
            sf_secret = os.getenv('SNOWFLAKE_SECRET')
            if sf_secret is None:
                raise ValueError("SNOWFLAKE_SECRET environment variable is not set and credentials file not found")
            sf_account = json.loads(sf_secret)
        
        creds = {
            "SF_ACCOUNT": sf_account["SF_ACCOUNT"],
            "SF_USER": sf_account["SF_USER"],
            "rsa_key": sf_account["rsa_key"]
        }
        p_key = serialization.load_pem_private_key(
            str.encode(creds["rsa_key"]),
            password=None,
            backend=default_backend(),
        )
        pkb = p_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        conn_params = {
            "account": creds["SF_ACCOUNT"],
            "user": creds["SF_USER"],
            "role": role,
            "warehouse": wh,
            "database": db,
            "schema": schema,
            "private_key": pkb,
            "arrow_number_to_decimal": True
        }
        connection = connector.connect(**conn_params)
        logger.info("Successfully connected to Snowflake")
        return connection
    except Exception as e:
        logger.error(f"Error connecting to Snowflake: {str(e)}")
        raise


def fetch_data_from_snowflake(query):
    """
    Execute SQL query and return data as pandas DataFrame
    Args:
        query (str): SQL query to execute
    Returns:
        DataFrame: Pandas DataFrame with query results
    """
    conn = None
    try:
        conn = get_snowflake_connection()
        cur = conn.cursor()
        cur.execute("USE WAREHOUSE REPORTING_WH")
        cur.execute(query)
        df = cur.fetch_pandas_all()
        logger.info(f"Fetched {len(df)} records from Snowflake")
        return df
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()
            logger.info("Snowflake connection closed")


def prepare_dataframe_for_export(df):
    """
    Prepare DataFrame for export by handling datetime columns
    Args:
        df (DataFrame): Pandas DataFrame
    Returns:
        DataFrame: Prepared DataFrame
    """
    df_copy = df.copy()
    try:
        for col in df_copy.columns:
            if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        logger.info("DataFrame prepared for export")
        return df_copy
    except Exception as e:
        logger.error(f"Error preparing DataFrame: {str(e)}")
        return None


def dataframe_to_csv_string(df):
    """
    Convert DataFrame to CSV string without saving to disk
    Args:
        df (DataFrame): Pandas DataFrame
    Returns:
        str: CSV formatted string, or None on error
    """
    if df is None or df.empty:
        logger.warning("DataFrame is empty, skipping CSV conversion")
        return None
    try:
        df_prepared = prepare_dataframe_for_export(df)
        csv_string = df_prepared.to_csv(index=False, encoding='utf-8')
        csv_size = len(csv_string) / 1024
        logger.info(f"CSV data prepared ({csv_size:.2f} KB)")
        return csv_string
    except Exception as e:
        logger.error(f"Error converting to CSV: {str(e)}")
        return None


# ==================== SENDGRID FUNCTIONS ====================
def send_email_with_attachment(api_key, from_email, to_emails, csv_data, filename, subject, html_content, cc_emails=None, bcc_emails=None):
    """
    Send email using SendGrid API
    Args:
        api_key (str): SendGrid API key
        from_email (str): Sender email address
        to_emails (list): List of recipient email addresses
        csv_data (str): CSV data as string
        filename (str): Name of the attachment file
        subject (str): Email subject
        html_content (str): HTML content of the email
        cc_emails (list, optional): List of CC email addresses
        bcc_emails (list, optional): List of BCC email addresses
    """
    try:
        message = Mail(from_email=from_email, subject=subject, html_content=html_content)
        personalization = Personalization()
        for email in to_emails:
            personalization.add_to(Email(email))
        if cc_emails:
            for email in cc_emails:
                personalization.add_cc(Email(email))
        if bcc_emails:
            for email in bcc_emails:
                personalization.add_bcc(Email(email))
        message.add_personalization(personalization)
        encoded_file = base64.b64encode(csv_data.encode('utf-8')).decode()
        attached_file = Attachment(
            FileContent(encoded_file),
            FileName(filename),
            FileType("text/csv"),
            Disposition("attachment")
        )
        message.attachment = attached_file
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logger.info(f"Email sent successfully. Status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise


def main():
    """Main execution function"""
    try:
        df = fetch_data_from_snowflake(QUERY)
        csv_data = dataframe_to_csv_string(df)
        send_email_with_attachment(
            API_KEY,
            FROM_EMAIL,
            TO_EMAILS,
            csv_data,
            FILENAME,
            SUBJECT,
            HTML_CONTENT,
            CC_EMAILS,
            BCC_EMAILS
        )
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")


if __name__ == "__main__":
    exit(main())