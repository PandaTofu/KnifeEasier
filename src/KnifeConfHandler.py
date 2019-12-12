#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser
from functools import partial


SEC_KNIFE_CONF = "knife_conf"
OPT_BASELINE = "baseline"
OPT_HW_MODULE = "hw_module"
OPT_KNIFE_DIR = "knife_dir"
OPT_CHANGE_BUILD_CONF = "modify_build_configuration"
OPT_EXPECTED_RESULT = "expected_result"
OPT_REF = "reference"
OPT_NO_REF = "no_reference"
OPT_PURPOSE = "purpose"
OPT_RECIPIENTS = "recipients_list"

CONF_TO_HW_MODULE = {"FSM-r3": "fsm3",
                     "FSM-r4": "fsm4",
                     "COMMON FDD build (frozen FSM-r2 + FSM-r3 + AirScale)": "fsm23air",
                     "COMMON": "fsm23air"}

KEY_BASELINE = "knife_request[baseline]"
KEY_HW_MODULE = "knife_request[module]"
KEY_KNIFE_DIR = "knife_request[knife_dir]"
KEY_FORCE_KNIFE_DIR = "knife_request[force_knife_dir]"
KEY_CHANGE_BUILD_CONF = "change_components"
KEY_EXPECTED_RESULT = "knife_request[flags][]"
KEY_SC = "knife_request[rebuild_sc][]"
KEY_REF_ID = "knife_request[reference_id]"
KEY_REF_TYPE = "knife_request[reference_type]"
KEY_NO_REF = "knife_request[no_reference]"
KEY_PURPOSE ="knife_request[purpose]"
KEY_RECIPIENTS = "knife_request[recipients_list]_values[]"
KEY_RECEIVER = "knife_request[result_receiver]"

DISP_TO_RESULT = {"StandarBTS package (BTSSM)": "bts",
                  "Test packages": "test"}


class KnifeConfHandler():
    def __init__(self):
        self.knife_conf = None
        self.cfParser = configparser.ConfigParser()
        self.cfParser.add_section(SEC_KNIFE_CONF)

    def getConf(self, key):
        return self.cfParser[SEC_KNIFE_CONF].get(key, "")

    def getFlag(self, key):
        return self.cfParser.getboolean(SEC_KNIFE_CONF, key)

    def setConf(self, key, value):
        self.cfParser.set(SEC_KNIFE_CONF, key, value)

    def getBaseline(self):
        return self.getConf(OPT_BASELINE)

    def getHWModule(self):
        return self.getConf(OPT_HW_MODULE)

    def getKnifeDir(self):
        return self.getConf(OPT_KNIFE_DIR)

    def getChangeBuildConf(self):
        return self.getFlag(OPT_CHANGE_BUILD_CONF)

    def getExpectedResult(self):
        return self.getConf(OPT_EXPECTED_RESULT)

    def getRefName(self):
        return self.getConf(OPT_REF)

    def getNoRef(self):
        return self.getFlag(OPT_NO_REF)

    def getPurpose(self):
        return self.getConf(OPT_PURPOSE)

    def getRecipients(self):
        return self.getConf(OPT_RECIPIENTS)

    def setBaseline(self, value):
        self.setConf(OPT_BASELINE, value)

    def setHWModule(self, value):
        self.setConf(OPT_HW_MODULE, value)

    def setKnifeDir(self, value):
        self.setConf(OPT_KNIFE_DIR, value)

    def setChangeBuildConf(self, flag):
        self.setConf(OPT_CHANGE_BUILD_CONF, str(flag))

    def setExpectedResult(self, value):
        expectedResults = self.getConf(OPT_EXPECTED_RESULT)
        if not expectedResults:
            self.setConf(OPT_EXPECTED_RESULT, value)
        else:
            result_list = expectedResults.split(',')
            if value not in result_list:
                expectedResults += ',' + value
                self.setConf(OPT_EXPECTED_RESULT, expectedResults)

    def setRefName(self, value):
        self.setConf(OPT_REF, value)

    def setNoRef(self, flag):
        self.setConf(OPT_NO_REF, str(flag))

    def setPurpose(self, value):
        self.setConf(OPT_PURPOSE, value)

    def setRecipients(self, value):
        self.setConf(OPT_RECIPIENTS, value)

    def readConf(self, fileName):
        self.cfParser = configparser.ConfigParser()
        self.cfParser.read(fileName)

    def writeConf(self, fileName):
        self.cfParser.write(open(fileName, "w"))

    def converKnifeConf(self, refID):
        knife_conf = list()
        knife_conf.append(("knife_request[knife_type]", "fb"))
        knife_conf.append(("knife_request[request_type]", "baseline"))
        knife_conf.append((KEY_BASELINE, self.getBaseline()))
        knife_conf.append((KEY_HW_MODULE, CONF_TO_HW_MODULE[self.getHWModule()]))
        knife_conf.append(("knife_request[sc]", ""))
        knife_conf.append(("knife_request[customer_knife]", 0))
        knife_conf.append(("use_knife_package", 1))
        knife_conf.append((KEY_KNIFE_DIR, self.getKnifeDir()))
        knife_conf.append(("knife_request[force_knife_dir]", 0))
        knife_conf.append(("knife_request[rebuild_sc][]", "OAM"))
        knife_conf.append((KEY_CHANGE_BUILD_CONF, int(self.getChangeBuildConf())))
        knife_conf.append(("knife_request[dcm_knife]", 0))
        knife_conf.append(("knife_request[impact_wcdma]", 0))
        knife_conf.append(("knife_request[server]", "http://10.129.142.130:80"))
        knife_conf.append(("knife_request[version_number]", 99))
        for result in set(self.getExpectedResult().split(',')):
            knife_conf.append((KEY_EXPECTED_RESULT, DISP_TO_RESULT[result]))
        if self.getRefName().startswith("Fault"):
            knife_conf.append((KEY_REF_TYPE, "Fault"))
        else:
            knife_conf.append((KEY_REF_TYPE, "Feature"))
        knife_conf.append((KEY_REF_ID, refID))
        knife_conf.append((KEY_NO_REF, int(self.getNoRef())))
        knife_conf.append((KEY_PURPOSE, self.getPurpose()))
        knife_conf.append(("knife_request[knife_info]", ""))
        knife_conf.append((KEY_RECIPIENTS, self.getRecipients()))
        knife_conf.append(("knife_request[recipients_list]", ""))
        knife_conf.append((KEY_RECEIVER, self.getRecipients()))
        knife_conf.append(("knife_request[tester_id]", ""))
        return knife_conf

