// Copyright (c) 2010 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "chrome/browser/chromeos/customization_document.h"

#include "base/file_util.h"
#include "base/json/json_reader.h"
#include "base/logging.h"
#include "base/string_tokenizer.h"
#include "base/string_util.h"

// Manifest attributes names.

namespace {

const char kVersionAttr[] = "version";
const char kDefaultAttr[] = "default";
const char kInitialLocaleAttr[] = "initial_locale";
const char kInitialTimezoneAttr[] = "initial_timezone";
const char kKeyboardLayoutAttr[] = "keyboard_layout";
const char kRegistrationUrlAttr[] = "registration_url";
const char kHwidMapAttr[] = "hwid_map";
const char kHwidMaskAttr[] = "hwid_mask";
const char kSetupContentAttr[] = "setup_content";
const char kHelpPageAttr[] = "help_page";
const char kEulaPageAttr[] = "eula_page";
const char kAppContentAttr[] = "app_content";
const char kInitialStartPageAttr[] = "initial_start_page";
const char kSupportPageAttr[] = "support_page";

const char kAcceptedManifestVersion[] = "1.0";

const char kHWIDPath[] = "/sys/devices/platform/chromeos_acpi/HWID";
const char kVPDPath[] = "/var/log/vpd_2.0.txt";

}  // anonymous namespace

namespace chromeos {

// CustomizationDocument implementation.
bool CustomizationDocument::LoadManifestFromFile(
    const FilePath& manifest_path) {
  std::string manifest;
  if (!file_util::ReadFileToString(manifest_path, &manifest))
    return false;
  return LoadManifestFromString(manifest);
}

bool CustomizationDocument::LoadManifestFromString(
    const std::string& manifest) {
  scoped_ptr<Value> root(base::JSONReader::Read(manifest, true));
  DCHECK(root.get() != NULL);
  if (root.get() == NULL)
    return false;
  DCHECK(root->GetType() == Value::TYPE_DICTIONARY);
  if (root->GetType() == Value::TYPE_DICTIONARY) {
    root_.reset(static_cast<DictionaryValue*>(root.release()));
    std::string result;
    if (root_->GetString(kVersionAttr, &result) &&
        result == kAcceptedManifestVersion)
      return true;

    LOG(ERROR) << "Wrong customization manifest version";
    root_.reset(NULL);
  }
  return false;
}

std::string CustomizationDocument::GetLocaleSpecificString(
    const std::string& locale,
    const std::string& dictionary_name,
    const std::string& entry_name) const {
  DictionaryValue* dictionary_content = NULL;
  if (!root_->GetDictionary(dictionary_name, &dictionary_content))
    return std::string();

  DictionaryValue* locale_dictionary = NULL;
  if (dictionary_content->GetDictionary(locale, &locale_dictionary)) {
    std::string result;
    if (locale_dictionary->GetString(entry_name, &result))
      return result;
  }

  DictionaryValue* default_dictionary = NULL;
  if (dictionary_content->GetDictionary(kDefaultAttr, &default_dictionary)) {
    std::string result;
    if (default_dictionary->GetString(entry_name, &result))
      return result;
  }

  return std::string();
}

// StartupCustomizationDocument implementation.
bool StartupCustomizationDocument::LoadManifestFromString(
    const std::string& manifest) {
  if (!CustomizationDocument::LoadManifestFromString(manifest)) {
    return false;
  }

  root_->GetString(kInitialLocaleAttr, &initial_locale_);
  root_->GetString(kInitialTimezoneAttr, &initial_timezone_);
  root_->GetString(kKeyboardLayoutAttr, &keyboard_layout_);
  root_->GetString(kRegistrationUrlAttr, &registration_url_);

  std::string hwid = GetHWID();
  if (!hwid.empty()) {
    ListValue* hwid_list = NULL;
    if (root_->GetList(kHwidMapAttr, &hwid_list)) {
      for (size_t i = 0; i < hwid_list->GetSize(); ++i) {
        DictionaryValue* hwid_dictionary = NULL;
        std::string hwid_mask;
        if (hwid_list->GetDictionary(i, &hwid_dictionary) &&
            hwid_dictionary->GetString(kHwidMaskAttr, &hwid_mask)) {
          if (MatchPattern(hwid, hwid_mask)) {
            // If HWID for this machine matches some mask, use HWID specific
            // settings.
            std::string result;
            if (hwid_dictionary->GetString(kInitialLocaleAttr, &result))
              initial_locale_ = result;

            if (hwid_dictionary->GetString(kInitialTimezoneAttr, &result))
              initial_timezone_ = result;

            if (hwid_dictionary->GetString(kKeyboardLayoutAttr, &result))
              keyboard_layout_ = result;
          }
          // Don't break here to allow other entires to be applied if match.
        } else {
          LOG(ERROR) << "Syntax error in customization manifest";
        }
      }
    }
  } else {
    LOG(ERROR) << "Can't read HWID from " << kHWIDPath;
  }

  VPDMap vpd_map;
  if (ParseVPD(GetVPD(), &vpd_map)) {
    InitFromVPD(vpd_map, kInitialLocaleAttr, &initial_locale_);
    InitFromVPD(vpd_map, kInitialTimezoneAttr, &initial_timezone_);
    InitFromVPD(vpd_map, kKeyboardLayoutAttr, &keyboard_layout_);
  }

  return true;
}

std::string StartupCustomizationDocument::GetHWID() const {
  // TODO(dpolukhin): move to SystemLibrary to be reusable.
  std::string hwid;
  FilePath hwid_file_path(kHWIDPath);
  if (!file_util::ReadFileToString(hwid_file_path, &hwid))
    LOG(ERROR) << "Can't read HWID from " << kHWIDPath;
  return hwid;
}

std::string StartupCustomizationDocument::GetVPD() const {
  // TODO(dpolukhin): move to SystemLibrary to be reusable.
  std::string vpd;
  FilePath vpd_file_path(kVPDPath);
  if (!file_util::ReadFileToString(vpd_file_path, &vpd))
    LOG(ERROR) << "Can't read VPD from " << kVPDPath;
  return vpd;
}

bool StartupCustomizationDocument::ParseVPD(const std::string& vpd_string,
                                            VPDMap* vpd_map) {
  // TODO(dpolukhin): move to SystemLibrary to be reusable.
  const char kDelimiterChars[] = "= \n";
  const char kQuotaChars[] = "\"\'";

  StringTokenizer tok(vpd_string, kDelimiterChars);
  tok.set_quote_chars(kQuotaChars);
  tok.set_options(StringTokenizer::RETURN_DELIMS);
  bool next_is_equal = false;
  bool next_is_value = false;
  std::string name;
  std::string value;
  while (tok.GetNext()) {
    // Skip all delimiters that are not '='.
    if (tok.token_is_delim() && tok.token() != "=")
      continue;

    if (next_is_equal) {
      if (tok.token() != "=")
        break;

      next_is_equal = false;
      next_is_value = true;
    } else if (next_is_value) {
      TrimString(tok.token(), kQuotaChars, &value);
      next_is_value = false;

      if (!vpd_map->insert(VPDMap::value_type(name, value)).second) {
        LOG(ERROR) << "Identical keys in VPD " << name;
        return false;
      }
    } else {
      TrimString(tok.token(), kQuotaChars, &name);
      next_is_equal = true;
    }
  }

  if (next_is_equal || next_is_value) {
    LOG(ERROR) << "Syntax error in VPD " << vpd_string;
    return false;
  }

  return true;
}

void StartupCustomizationDocument::InitFromVPD(
    const VPDMap& vpd_map, const char* attr, std::string* value) {
  VPDMap::const_iterator it = vpd_map.find(attr);
  if (it != vpd_map.end())
    *value = it->second;
}

std::string StartupCustomizationDocument::GetHelpPage(
    const std::string& locale) const {
  return GetLocaleSpecificString(locale, kSetupContentAttr, kHelpPageAttr);
}

std::string StartupCustomizationDocument::GetEULAPage(
    const std::string& locale) const {
  return GetLocaleSpecificString(locale, kSetupContentAttr, kEulaPageAttr);
}

// ServicesCustomizationDocument implementation.
std::string ServicesCustomizationDocument::GetInitialStartPage(
    const std::string& locale) const {
  return GetLocaleSpecificString(
      locale, kAppContentAttr, kInitialStartPageAttr);
}

std::string ServicesCustomizationDocument::GetSupportPage(
    const std::string& locale) const {
  return GetLocaleSpecificString(
      locale, kAppContentAttr, kSupportPageAttr);
}

}  // namespace chromeos