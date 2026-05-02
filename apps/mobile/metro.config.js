// Default Metro config for Expo (SDK 51).
// Kept explicit so consumers can extend it later (e.g. monorepo paths).
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

module.exports = config;
