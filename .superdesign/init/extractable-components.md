# Extractable components

## SiteHeader
- Source: `site/chrome.js` (`lockupHead`, `rule`, `renderHeader`, `wireMenu`)
- Category: layout
- Description: shared asterisk/brief-bar header, navigation, language and menu
- Extractable props: activePage, ownLanguageControl
- Hardcoded: asterisk SVG, label `brief bar`, navigation structure, colour rule

## SiteFooter
- Source: `site/chrome.js` (`lockupFoot`, `renderFooter`, `wireTheme`)
- Category: layout
- Description: welance provenance and grouped site navigation
- Extractable props: none
- Hardcoded: welance wordmark, asterisk, navigation groups

The basic calculator primitives are small page-local HTML/CSS patterns and
should remain inline rather than becoming canvas components.
