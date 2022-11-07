# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import sys
import requests
import frappe
import chilkat
import json
import re
from frappe import _
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password
from erpnext_dhlshipping.erpnext_dhlshipping.utils import show_error_alert

DHL_PROVIDER = 'DHL'


class DHL(Document):
    pass


class DHLUtils():
    def __init__(self):
        self.user_key = get_decrypted_password(
            'DHL', 'DHL', 'api_password', raise_exception=False)
        self.user_id, self.enabled = frappe.db.get_value(
            'DHL', 'DHL', ['api_id', 'enabled'])

        if not self.enabled:
            link = frappe.utils.get_link_to_form(
                'DHL', 'DHL', frappe.bold('DHL Settings'))
            frappe.throw(
                _('Please enable DHL Integration in {0}'.format(link)), title=_('Mandatory'))

    def get_available_services(self, delivery_to_type, pickup_address,
                               delivery_address, shipment_parcel, description_of_content, pickup_date,
                               value_of_goods, pickup_contact=None, delivery_contact=None):
        # Retrieve rates at DHL from specification stated.
        if not self.enabled or not self.user_id or not self.user_key:
            return []

        # Get My Authorization token.
        self.set_letmeship_specific_fields(pickup_contact, delivery_contact)
        pickup_address.address_title = self.trim_address(pickup_address)
        delivery_address.address_title = self.trim_address(delivery_address)
        parcel_list = self.get_parcel_list(
            json.loads(shipment_parcel), description_of_content)

        url = 'https://api-sandbox.dhl.com'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Access-Control-Allow-Origin': 'string'
        }
        payload = self.generate_payload(
            pickup_address=pickup_address,
            pickup_contact=pickup_contact,
            delivery_address=delivery_address,
            delivery_contact=delivery_contact,
            description_of_content=description_of_content,
            value_of_goods=value_of_goods,
            parcel_list=parcel_list,
            pickup_date=pickup_date
        )

        try:
            available_services = []
            response_data = requests.post(
                url=url,
                auth=(self.api_id, self.api_password),
                headers=headers,
                data=json.dumps(payload)
            )
            response_data = json.loads(response_data.text)
            if 'serviceList' in response_data:
                for response in response_data['serviceList']:
                    available_service = self.get_service_dict(response)
                    available_services.append(available_service)

                return available_services
            else:
                frappe.throw(_('An Error occurred while fetching DHL prices: {0}')
                             .format(response_data['message']))
        except Exception:
            show_error_alert("fetching DHL prices")

        return []

    def create_shipment(self, pickup_address, delivery_address, shipment_parcel, description_of_content,
                        pickup_date, value_of_goods, service_info, pickup_contact=None, delivery_contact=None):
        # Create a transaction at DHL
        if not self.enabled or not self.api_id or not self.api_password:
            return []

        rest = chilkat.CkRest()

        #  URL: https://cig.dhl.de/services/sandbox/soap
        bTls = True
        port = 443
        bAutoReconnect = True
        success = rest.Connect("cig.dhl.de", port, bTls, bAutoReconnect)
        if (success != True):
            print("ConnectFailReason: " + str(rest.get_ConnectFailReason()))
            print(rest.lastErrorText())
            sys.exit()

        rest.SetAuthBasic(DEVELOPER_ID, DEVELOPER_PASSWORD)

        #  See the Online Tool for Generating XML Creation Code
        xml = chilkat.CkXml()
        xml.put_Tag("soapenv:Envelope")
        xml.AddAttribute(
            "xmlns:soapenv", "http://schemas.xmlsoap.org/soap/envelope/")
        xml.AddAttribute("xmlns:cis", "http://dhl.de/webservice/cisbase")
        xml.AddAttribute(
            "xmlns:bus", "http://dhl.de/webservices/businesscustomershipping")
        xml.UpdateChildContent(
            "soapenv:Header|cis:Authentification|cis:user", '2222222222_01')
        xml.UpdateChildContent(
            "soapenv:Header|cis:Authentification|cis:signature", 'pass')
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|bus:Version|majorRelease", "2")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|bus:Version|minorRelease", "0")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|sequenceNumber", "01")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|product", "V01PAK")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|cis:accountNumber", "22222222220101")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|customerReference", "Sendungsreferenz")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|shipmentDate", "2022-10-04")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|returnShipmentAccountNumber", "12341234567890")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|returnShipmentReference", "Retouren-Sendungsreferenz")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|ShipmentItem|weightInKG", "10")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|ShipmentItem|lengthInCM", "120")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|ShipmentItem|widthInCM", "60")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|ShipmentItem|heightInCM", "60")
        xml.UpdateAttrAt(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|Service|VisualCheckOfAge", True, "active", "1")
        xml.UpdateAttrAt(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|Service|VisualCheckOfAge", True, "type", "A16")
        xml.UpdateAttrAt(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|Service|PreferredLocation", True, "active", "0")
        xml.UpdateAttrAt(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|Service|PreferredLocation", True, "details", "?")
        xml.UpdateAttrAt(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|Service|PreferredNeighbour", True, "active", "0")
        xml.UpdateAttrAt(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|Service|PreferredNeighbour", True, "details", "?")
        xml.UpdateAttrAt(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|Service|GoGreen", True, "active", "1")
        xml.UpdateAttrAt(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|Service|Personally", True, "active", "0")
        xml.UpdateAttrAt(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|Service|CashOnDelivery", True, "active", "1")
        xml.UpdateAttrAt(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|Service|CashOnDelivery", True, "codAmount", "23.25")
        xml.UpdateAttrAt(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|Service|AdditionalInsurance", True, "active", "1")
        xml.UpdateAttrAt("soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|Service|AdditionalInsurance",
                         True, "insuranceAmount", "2500")
        xml.UpdateAttrAt(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|Service|BulkyGoods", True, "active", "1")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|Notification|recipientEmailAddress", "no-reply@deutschepost.de")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|BankData|cis:accountOwner", "Max Mustermann")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|BankData|cis:bankName", "Postbank")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|BankData|cis:iban", "DE77100100100123456789")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|BankData|cis:note1", "note 1")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|BankData|cis:note2", "note 2")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|BankData|cis:bic", "PBNKDEFFXXX")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ShipmentDetails|BankData|cis:accountreference", "?")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Name|cis:name1", "DHL Paket GmbH")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Name|cis:name2", "")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Name|cis:name3", "")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Address|cis:streetName", "Sträßchensweg")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Address|cis:streetNumber", "10")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Address|cis:addressAddition", "?")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Address|cis:dispatchingInformation", "?")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Address|cis:zip", "53113")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Address|cis:city", "Bonn")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Address|cis:Origin|cis:country", "Deutschland")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Address|cis:Origin|cis:countryISOCode", "DE")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Address|cis:Origin|cis:state", "?")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Communication|cis:phone", "")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Communication|cis:email", "")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Shipper|Communication|cis:contactPerson", "")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|cis:name1", "DHL Paket GmbH")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|Address|cis:name2", "")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|Address|cis:name3", "")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|Address|cis:streetName", "Charles-de-Gaulle-Str.")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|Address|cis:streetNumber", "20")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|Address|cis:addressAddition", "?")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|Address|cis:dispatchingInformation", "?")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|Address|cis:zip", "53113")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|Address|cis:city", "Bonn")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|Address|cis:Origin|cis:country", "Deutschland")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|Address|cis:Origin|cis:countryISOCode", "DE")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|Address|cis:Origin|cis:state", "?")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|Communication|cis:phone", "")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|Communication|cis:email", "")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|Receiver|Communication|cis:contactPerson", "")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Name|cis:name1", "DHL Paket GmbH")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Name|cis:name2", "")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Name|cis:name3", "")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Address|cis:streetName", "Sträßchensweg")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Address|cis:streetNumber", "10")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Address|cis:addressAddition", "?")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Address|cis:dispatchingInformation", "?")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Address|cis:zip", "53113")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Address|cis:city", "Bonn")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Address|cis:Origin|cis:country", "Deutschland")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Address|cis:Origin|cis:countryISOCode", "DE")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Address|cis:Origin|cis:state", "?")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Communication|cis:phone", "")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Communication|cis:email", "")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|Shipment|ReturnReceiver|Communication|cis:contactPerson", "")
        xml.UpdateAttrAt(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|PrintOnlyIfCodeable", True, "active", "1")
        xml.UpdateChildContent(
            "soapenv:Body|bus:CreateShipmentOrderRequest|ShipmentOrder|labelResponseType", "URL")

        rest.AddHeader("Content-Type", "application/xml")

        sbRequestBody = chilkat.CkStringBuilder()
        xml.GetXmlSb(sbRequestBody)
        sbResponseBody = chilkat.CkStringBuilder()
        success = rest.FullRequestSb(
            "POST", "/services/sandbox/soap", sbRequestBody, sbResponseBody)
        if (success != True):
            print(rest.lastErrorText())
            sys.exit()

        respStatusCode = rest.get_ResponseStatusCode()
        if (respStatusCode >= 400):
            print("Response Status Code = " + str(respStatusCode))
            print("Response Header:")
            print(rest.responseHeader())
            print("Response Body:")
            print(sbResponseBody.getAsString())
            sys.exit()

        xmlResponse = chilkat.CkXml()
        xmlResponse.LoadSb(sbResponseBody, True)

        #  See the Online Tool for Generating XML Parse Code

        soap_Envelope_xmlns_bcs = xmlResponse.getAttrValue("xmlns:bcs")
        soap_Envelope_xmlns_cis = xmlResponse.getAttrValue("xmlns:cis")
        soap_Envelope_xmlns_soap = xmlResponse.getAttrValue("xmlns:soap")
        soap_Envelope_xmlns_xsi = xmlResponse.getAttrValue("xmlns:xsi")
        soapenv_Header_xmlns_soapenv = xmlResponse.chilkatPath(
            "soapenv:Header|(xmlns:soapenv)")
        majorRelease = xmlResponse.GetChildIntValue(
            "soap:Body|bcs:CreateShipmentOrderResponse|bcs:Version|majorRelease")
        minorRelease = xmlResponse.GetChildIntValue(
            "soap:Body|bcs:CreateShipmentOrderResponse|bcs:Version|minorRelease")
        statusCode = xmlResponse.GetChildIntValue(
            "soap:Body|bcs:CreateShipmentOrderResponse|Status|statusCode")
        statusText = xmlResponse.getChildContent(
            "soap:Body|bcs:CreateShipmentOrderResponse|Status|statusText")
        statusMessage = xmlResponse.getChildContent(
            "soap:Body|bcs:CreateShipmentOrderResponse|Status|statusMessage")
        sequenceNumber = xmlResponse.GetChildIntValue(
            "soap:Body|bcs:CreateShipmentOrderResponse|CreationState|sequenceNumber")
        # statusCode = xmlResponse.GetChildIntValue(
        #     "soap:Body|bcs:CreateShipmentOrderResponse|CreationState|LabelData|Status|statusCode")
        # statusText = xmlResponse.getChildContent(
        #     "soap:Body|bcs:CreateShipmentOrderResponse|CreationState|LabelData|Status|statusText")
        # statusMessage = xmlResponse.getChildContent(
        #     "soap:Body|bcs:CreateShipmentOrderResponse|CreationState|LabelData|Status|statusMessage")
        cis_shipmentNumber = xmlResponse.getChildContent(
            "soap:Body|bcs:CreateShipmentOrderResponse|CreationState|LabelData|cis:shipmentNumber")
        labelUrl = xmlResponse.getChildContent(
            "soap:Body|bcs:CreateShipmentOrderResponse|CreationState|LabelData|labelUrl")

        self.set_letmeship_specific_fields(pickup_contact, delivery_contact)
        pickup_address.address_title = self.trim_address(pickup_address)
        delivery_address.address_title = self.trim_address(delivery_address)
        parcel_list = self.get_parcel_list(
            json.loads(shipment_parcel), description_of_content)

        url = 'https://api.letmeship.com/v1/shipments'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Access-Control-Allow-Origin': 'string'
        }
        payload = self.generate_payload(
            pickup_address=pickup_address,
            pickup_contact=pickup_contact,
            delivery_address=delivery_address,
            delivery_contact=delivery_contact,
            description_of_content=description_of_content,
            value_of_goods=value_of_goods,
            parcel_list=parcel_list,
            pickup_date=pickup_date,
            service_info=service_info)
        try:
            response_data = requests.post(
                url=url,
                auth=(self.api_id, self.api_password),
                headers=headers,
                data=json.dumps(payload)
            )
            response_data = json.loads(response_data.text)
            if 'shipmentId' in response_data:
                shipment_amount = response_data['service']['priceInfo']['totalPrice']
                awb_number = ''
                url = 'https://api.letmeship.com/v1/shipments/{id}'.format(
                    id=response_data['shipmentId'])
                tracking_response = requests.get(url, auth=(
                    self.api_id, self.api_password), headers=headers)
                tracking_response_data = json.loads(tracking_response.text)
                if 'trackingData' in tracking_response_data:
                    for parcel in tracking_response_data['trackingData']['parcelList']:
                        if 'awbNumber' in parcel:
                            awb_number = parcel['awbNumber']
                return {
                    'service_provider': DHL_PROVIDER,
                    'shipment_id': response_data['shipmentId'],
                    'carrier': service_info['carrier'],
                    'carrier_service': service_info['service_name'],
                    'shipment_amount': shipment_amount,
                    'awb_number': awb_number,
                }
            elif 'message' in response_data:
                frappe.throw(_('An Error occurred while creating Shipment: {0}')
                             .format(response_data['message']))
        except Exception:
            show_error_alert("creating LetMeShip Shipment")

    def get_label(self, shipment_id):
        # Retrieve shipment label from LetMeShip
        try:
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Access-Control-Allow-Origin': 'string'
            }
            url = 'https://api.letmeship.com/v1/shipments/{id}/documents?types=LABEL'.format(
                id=shipment_id)
            shipment_label_response = requests.get(
                url,
                auth=(self.api_id, self.api_password),
                headers=headers
            )
            shipment_label_response_data = json.loads(
                shipment_label_response.text)
            if 'documents' in shipment_label_response_data:
                for label in shipment_label_response_data['documents']:
                    if 'data' in label:
                        return json.dumps(label['data'])
            else:
                frappe.throw(_('Error occurred while printing Shipment: {0}')
                             .format(shipment_label_response_data['message']))
        except Exception:
            show_error_alert("printing LetMeShip Label")

    def get_tracking_data(self, shipment_id):
        from erpnext_dhlshipping.erpnext_dhlshipping.utils import get_tracking_url
        # return letmeship tracking data
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Access-Control-Allow-Origin': 'string'
        }
        try:
            url = 'https://api.letmeship.com/v1/tracking?shipmentid={id}'.format(
                id=shipment_id)
            tracking_data_response = requests.get(
                url,
                auth=(self.api_id, self.api_password),
                headers=headers
            )
            tracking_data = json.loads(tracking_data_response.text)
            if 'awbNumber' in tracking_data:
                tracking_status = 'In Progress'
                if tracking_data['lmsTrackingStatus'].startswith('DELIVERED'):
                    tracking_status = 'Delivered'
                if tracking_data['lmsTrackingStatus'] == 'RETURNED':
                    tracking_status = 'Returned'
                if tracking_data['lmsTrackingStatus'] == 'LOST':
                    tracking_status = 'Lost'
                tracking_url = get_tracking_url(
                    carrier=tracking_data['carrier'],
                    tracking_number=tracking_data['awbNumber']
                )
                return {
                    'awb_number': tracking_data['awbNumber'],
                    'tracking_status': tracking_status,
                    'tracking_status_info': tracking_data['lmsTrackingStatus'],
                    'tracking_url': tracking_url,
                }
            elif 'message' in tracking_data:
                frappe.throw(_('Error occurred while updating Shipment: {0}')
                             .format(tracking_data['message']))
        except Exception:
            show_error_alert("updating LetMeShip Shipment")

    def generate_payload(self, pickup_address, pickup_contact, delivery_address, delivery_contact,
                         description_of_content, value_of_goods, parcel_list, pickup_date, service_info=None):
        payload = {
            'pickupInfo': self.get_pickup_delivery_info(pickup_address, pickup_contact),
            'deliveryInfo': self.get_pickup_delivery_info(delivery_address, delivery_contact),
            'shipmentDetails': {
                'contentDescription': description_of_content,
                'shipmentType': 'PARCEL',
                'shipmentSettings': {
                    'saturdayDelivery': False,
                    'ddp': False,
                                'insurance': False,
                                'pickupOrder': False,
                                'pickupTailLift': False,
                                'deliveryTailLift': False,
                                'holidayDelivery': False,
                },
                'goodsValue': value_of_goods,
                'parcelList': parcel_list,
                'pickupInterval': {
                    'date': pickup_date
                }
            }
        }

        if service_info:
            payload['service'] = {
                'baseServiceDetails': {
                    'id': service_info['id'],
                    'name': service_info['service_name'],
                    'carrier': service_info['carrier'],
                    'priceInfo': service_info['price_info'],
                },
                'supportedExWorkType': [],
                'messages': [''],
                'description': '',
                'serviceInfo': '',
            }
            payload['shipmentNotification'] = {
                'trackingNotification': {
                    'deliveryNotification': True,
                    'problemNotification': True,
                    'emails': [],
                    'notificationText': '',
                },
                'recipientNotification': {
                    'notificationText': '',
                    'emails': []
                }
            }
            payload['labelEmail'] = True
        return payload

    def trim_address(self, address):
        # LetMeShip has a limit of 30 characters for Company field
        if len(address.address_title) > 30:
            return address.address_title[:30]

    def get_service_dict(self, response):
        """Returns a dictionary with service info."""
        available_service = frappe._dict()
        basic_info = response['baseServiceDetails']
        price_info = basic_info['priceInfo']
        available_service.service_provider = DHL_PROVIDER
        available_service.id = basic_info['id']
        available_service.carrier = basic_info['carrier']
        available_service.carrier_name = basic_info['name']
        available_service.service_name = ''
        available_service.is_preferred = 0
        available_service.real_weight = price_info['realWeight']
        available_service.total_price = price_info['netPrice']
        available_service.price_info = price_info
        return available_service

    def set_letmeship_specific_fields(self, pickup_contact, delivery_contact):
        pickup_contact.phone_prefix = pickup_contact.phone[:3]
        pickup_contact.phone = re.sub(
            '[^A-Za-z0-9]+', '', pickup_contact.phone[3:])

        pickup_contact.title = 'MS'
        if pickup_contact.gender == 'Male':
            pickup_contact.title = 'MR'

        delivery_contact.phone_prefix = delivery_contact.phone[:3]
        delivery_contact.phone = re.sub(
            '[^A-Za-z0-9]+', '', delivery_contact.phone[3:])

        delivery_contact.title = 'MS'
        if delivery_contact.gender == 'Male':
            delivery_contact.title = 'MR'

    def get_parcel_list(self, shipment_parcel, description_of_content):
        parcel_list = []
        for parcel in shipment_parcel:
            formatted_parcel = {}
            formatted_parcel['height'] = parcel.get('height')
            formatted_parcel['width'] = parcel.get('width')
            formatted_parcel['length'] = parcel.get('length')
            formatted_parcel['weight'] = parcel.get('weight')
            formatted_parcel['quantity'] = parcel.get('count')
            formatted_parcel['contentDescription'] = description_of_content
            parcel_list.append(formatted_parcel)
        return parcel_list

    def get_pickup_delivery_info(self, address, contact):
        return {
            'address': {
                'countryCode': address.country_code,
                'zip': address.pincode,
                'city': address.city,
                'street': address.address_line1,
                'addressInfo1': address.address_line2,
                'houseNo': '',
            },
            'company': address.address_title,
            'person': {
                'title': contact.title,
                'firstname': contact.first_name,
                'lastname': contact.last_name
            },
            'phone': {
                'phoneNumber': contact.phone,
                'phoneNumberPrefix': contact.phone_prefix
            },
            'email': contact.email
        }
