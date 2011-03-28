function runTests() {
  var getURL = chrome.extension.getURL;
  chrome.tabs.getSelected(null, function(tab) {
    var tabId = tab.id;

    chrome.test.runTests([
      // Navigates to a.html which includes b.html as an iframe. b.html
      // redirects to c.html.
      function iframe() {
        expect([
          [ "onBeforeNavigate",
            { frameId: 0,
              requestId: 0,
              tabId: 0,
              timeStamp: 0,
              url: getURL('a.html') }],
          [ "onCommitted",
            { frameId: 0,
              tabId: 0,
              timeStamp: 0,
              transitionQualifiers: [],
              transitionType: "link",
              url: getURL('a.html') }],
          [ "onBeforeNavigate",
            { frameId: 1,
              requestId: 0,
              tabId: 0,
              timeStamp: 0,
              url: getURL('b.html') }],
          [ "onDOMContentLoaded",
            { frameId: 0,
              tabId: 0,
              timeStamp: 0,
              url: getURL('a.html') }],
          [ "onCommitted",
            { frameId: 1,
              tabId: 0,
              timeStamp: 0,
              transitionQualifiers: [],
              transitionType: "auto_subframe",
              url: getURL('b.html') }],
          [ "onDOMContentLoaded",
            { frameId: 1,
              tabId: 0,
              timeStamp: 0,
              url: getURL('b.html') }],
          [ "onCompleted",
            { frameId: 1,
              tabId: 0,
              timeStamp: 0,
              url: getURL('b.html') }],
          [ "onCompleted",
            { frameId: 0,
              tabId: 0,
              timeStamp: 0,
              url: getURL('a.html') }],
          [ "onBeforeNavigate",
            { frameId: 1,
              requestId: 0,
              tabId: 0,
              timeStamp: 0,
              url: getURL('c.html') }],
          [ "onCommitted",
            { frameId: 1,
              tabId: 0,
              timeStamp: 0,
              transitionQualifiers: [],
              transitionType: "manual_subframe",
              url: getURL('c.html') }],
          [ "onDOMContentLoaded",
            { frameId: 1,
              tabId: 0,
              timeStamp: 0,
              url: getURL('c.html') }],
          [ "onCompleted",
            { frameId: 1,
              tabId: 0,
              timeStamp: 0,
              url: getURL('c.html') }]]);
        chrome.tabs.update(tabId, { url: getURL('a.html') });
      },

      // Navigates to d.html which includes e.html and f.html as iframes. To be
      // able to predict which iframe has which id, the iframe for f.html is
      // created by javascript. f.html then navigates to g.html.
      function iframeMultiple() {
        expect([
          [ "onBeforeNavigate",
            { frameId: 0,
              requestId: 0,
              tabId: 0,
              timeStamp: 0,
              url: getURL('d.html') }],
          [ "onCommitted",
            { frameId: 0,
              tabId: 0,
              timeStamp: 0,
              transitionQualifiers: [],
              transitionType: "link",
              url: getURL('d.html') }],
          [ "onBeforeNavigate",
            { frameId: 1,
              requestId: 0,
              tabId: 0,
              timeStamp: 0,
              url: getURL('e.html') }],
          [ "onDOMContentLoaded",
            { frameId: 0,
              tabId: 0,
              timeStamp: 0,
              url: getURL('d.html') }],
          [ "onCommitted",
            { frameId: 1,
              tabId: 0,
              timeStamp: 0,
              transitionQualifiers: [],
              transitionType: "auto_subframe",
              url: getURL('e.html') }],
          [ "onDOMContentLoaded",
            { frameId: 1,
              tabId: 0,
              timeStamp: 0,
              url: getURL('e.html') }],
          [ "onBeforeNavigate",
            { frameId: 2,
              requestId: 0,
              tabId: 0,
              timeStamp: 0,
              url: getURL('f.html') }],
          [ "onCompleted",
            { frameId: 1,
              tabId: 0,
              timeStamp: 0,
              url: getURL('e.html') }],
          [ "onCommitted",
            { frameId: 2,
              tabId: 0,
              timeStamp: 0,
              transitionQualifiers: [],
              transitionType: "auto_subframe",
              url: getURL('f.html') }],
          [ "onDOMContentLoaded",
            { frameId: 2,
              tabId: 0,
              timeStamp: 0,
              url: getURL('f.html') }],
          [ "onCompleted",
            { frameId: 2,
              tabId: 0,
              timeStamp: 0,
              url: getURL('f.html') }],
          [ "onCompleted",
            { frameId: 0,
              tabId: 0,
              timeStamp: 0,
              url: getURL('d.html') }],
          [ "onBeforeNavigate",
            { frameId: 2,
              requestId: 0,
              tabId: 0,
              timeStamp: 0,
              url: getURL('g.html') }],
          [ "onCommitted",
            { frameId: 2,
              tabId: 0,
              timeStamp: 0,
              transitionQualifiers: [],
              transitionType: "manual_subframe",
              url: getURL('g.html') }],
          [ "onDOMContentLoaded",
            { frameId: 2,
              tabId: 0,
              timeStamp: 0,
              url: getURL('g.html') }],
          [ "onCompleted",
            { frameId: 2,
              tabId: 0,
              timeStamp: 0,
              url: getURL('g.html') }]]);
        chrome.tabs.update(tabId, { url: getURL('d.html') });
      },
    ]);
  });
}