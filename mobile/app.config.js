const appJson = require("./app.json");

module.exports = () => {
  const config = appJson.expo;

  return {
    ...config,
    extra: {
      ...config.extra,
      backendUrl:
        process.env.EXPO_PUBLIC_BACKEND_URL ||
        config.extra?.backendUrl ||
        "https://api.crowscap.xyz",
      googleClientIdWeb: process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID_WEB || "",
      googleClientIdAndroid: process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID_ANDROID || "",
      googleClientIdIos: process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID_IOS || "",


    },
    android: {
      ...config.android,
      googleServicesFile:
        process.env.GOOGLE_SERVICES_JSON || "./google-services.json",
    },
  };
};
