local addonName, _ = ...

-- One folder per pack under here, each holding the clip file names MiniAuras ships.
local BASE_PATH = "Interface\\AddOns\\" .. addonName .. "\\Sounds\\"
-- One set of clips serves both Spanish clients.
-- The twenty names esMX words differently are spoken the esES way.
local LOCALES = { "esES", "esMX" }
local PACK_NAMES = { "Miguel", "Kate" }
local MINIAURAS = "MiniAuras"

---@return boolean handedOver false while MiniAuras has not published its API yet
local function RegisterPacks()
	local api = MiniAurasApi and MiniAurasApi.v1

	if not api or not api.RegisterVoicePack then
		return false
	end

	for i = 1, #PACK_NAMES do
		local name = PACK_NAMES[i]

		api:RegisterVoicePack({
			Name = name,
			Path = BASE_PATH .. name .. "\\",
			Locales = LOCALES,
		})
	end

	return true
end

if not RegisterPacks() then
	-- MiniAuras is an optional dependency, so it normally loads first. It can still arrive
	-- afterwards, and the packs are only offered once it has.
	local waiter = CreateFrame("Frame")

	waiter:RegisterEvent("ADDON_LOADED")
	waiter:SetScript("OnEvent", function(self, _, loaded)
		if loaded ~= MINIAURAS then
			return
		end

		-- Once MiniAuras has loaded, waiting longer cannot make the API appear.
		self:UnregisterAllEvents()
		RegisterPacks()
	end)
end
