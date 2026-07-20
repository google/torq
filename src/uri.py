#
# Copyright (C) 2026 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Enum defining known IANA URI schemes.

Tracked against the IANA Uniform Resource Identifier (URI) Schemes registry:
https://www.iana.org/assignments/uri-schemes/uri-schemes.xhtml
"""

from enum import StrEnum


class URIScheme(StrEnum):
  """
  Known URI schemes including all IANA Permanent schemes.
  """
  AAA = "aaa"
  AAAS = "aaas"
  ABOUT = "about"
  ACAP = "acap"
  ACCT = "acct"
  CAP = "cap"
  CID = "cid"
  COAP = "coap"
  COAP_TCP = "coap+tcp"
  COAP_WS = "coap+ws"
  COAPS = "coaps"
  COAPS_TCP = "coaps+tcp"
  COAPS_WS = "coaps+ws"
  CRID = "crid"
  DATA = "data"
  DAV = "dav"
  DICT = "dict"
  DNS = "dns"
  DOI = "doi"
  DTN = "dtn"
  EXAMPLE = "example"
  FILE = "file"
  FTP = "ftp"
  GEO = "geo"
  GIT = "git"
  GO = "go"
  GOPHER = "gopher"
  H323 = "h323"
  HTTP = "http"
  HTTPS = "https"
  IAX = "iax"
  ICAP = "icap"
  IM = "im"
  IMAP = "imap"
  INFO = "info"
  IPN = "ipn"
  IPP = "ipp"
  IPPS = "ipps"
  IRIS = "iris"
  IRIS_BEEP = "iris.beep"
  IRIS_LWZ = "iris.lwz"
  IRIS_XPC = "iris.xpc"
  IRIS_XPCS = "iris.xpcs"
  JABBER = "jabber"
  LDAP = "ldap"
  LEAPTOFROGANS = "leaptofrogans"
  MAILTO = "mailto"
  MID = "mid"
  MSRP = "msrp"
  MSRPS = "msrps"
  MT = "mt"
  MTQP = "mtqp"
  MUPDATE = "mupdate"
  NEWS = "news"
  NFS = "nfs"
  NI = "ni"
  NIH = "nih"
  NNTP = "nntp"
  OPAQUELOCKTOKEN = "opaquelocktoken"
  PKCS11 = "pkcs11"
  POP = "pop"
  PRES = "pres"
  RELOAD = "reload"
  RTSP = "rtsp"
  RTSPS = "rtsps"
  RTSPU = "rtspu"
  SERVICE = "service"
  SESSION = "session"
  SFTP = "sftp"
  SHTTP = "shttp"
  SIEVE = "sieve"
  SIP = "sip"
  SIPS = "sips"
  SMS = "sms"
  SNMP = "snmp"
  SOAP_BEEP = "soap.beep"
  SOAP_BEEPS = "soap.beeps"
  SSH = "ssh"
  STUN = "stun"
  STUNS = "stuns"
  SVN = "svn"
  TAG = "tag"
  TEL = "tel"
  TELNET = "telnet"
  TFTP = "tftp"
  THISMESSAGE = "thismessage"
  TIP = "tip"
  TN3270 = "tn3270"
  TTY = "tty"
  TURN = "turn"
  TURNS = "turns"
  TV = "tv"
  URN = "urn"
  VEMMI = "vemmi"
  VNC = "vnc"
  WS = "ws"
  WSS = "wss"
  XCON = "xcon"
  XCON_USERID = "xcon-userid"
  XMLRPC_BEEP = "xmlrpc.beep"
  XMLRPC_BEEPS = "xmlrpc.beeps"
  XMPP = "xmpp"
  Z39_50R = "z39.50r"
  Z39_50S = "z39.50s"

  @classmethod
  def is_valid_scheme(cls, scheme):
    return any(scheme == item.value for item in cls)
