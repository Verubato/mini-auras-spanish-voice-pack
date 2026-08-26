-- The addon is two calls into MiniAuras, so these stub its API and check what it was handed,
-- including the case where MiniAuras is not there yet when the file runs.

local fw = require("TestFramework")
local harness = require("AddonHarness")
local WowMock = require("WowMock")

local ADDON = "MiniAurasVoicePackSpanish"
local FILE = "src/MiniAurasVoicePackSpanish.lua"

---A stand-in for MiniAuras that records every pack handed to it.
---@param registered table
---@return table
local function NewApi(registered)
	return {
		v1 = {
			RegisterVoicePack = function(_, pack)
				registered[#registered + 1] = pack

				return true
			end,
		},
	}
end

---@param api table? what MiniAuras has published before the addon loads, if anything
local function LoadWith(api)
	WowMock.Install()

	_G.MiniAurasApi = api

	harness.LoadFiles(ADDON, { FILE }, {})
end

---@return table registered
local function Load()
	local registered = {}

	LoadWith(NewApi(registered))

	return registered
end

fw.describe(ADDON .. " - voice pack registration", function()
	fw.it("hands both packs over when the API is already there", function()
		local registered = Load()

		fw.eq(#registered, 2, "packs registered")
		fw.eq(registered[1].Name, "Miguel", "first pack name")
		fw.eq(registered[2].Name, "Kate", "second pack name")
	end)

	fw.it("points each pack at its own folder of clips", function()
		local registered = Load()

		fw.eq(
			registered[1].Path,
			"Interface\\AddOns\\MiniAurasVoicePackSpanish\\Sounds\\Miguel\\",
			"first pack path"
		)
		fw.eq(
			registered[2].Path,
			"Interface\\AddOns\\MiniAurasVoicePackSpanish\\Sounds\\Kate\\",
			"second pack path"
		)
	end)

	fw.it("offers the packs on both Spanish clients", function()
		local registered = Load()

		for i = 1, #registered do
			fw.eq(#registered[i].Locales, 2, "locale count for " .. registered[i].Name)
			fw.eq(registered[i].Locales[1], "esES", "first locale for " .. registered[i].Name)
			fw.eq(registered[i].Locales[2], "esMX", "second locale for " .. registered[i].Name)
		end
	end)

	fw.it("waits for a MiniAuras that loads after it", function()
		local registered = {}

		LoadWith(nil)

		fw.eq(#registered, 0, "nothing to register against")

		_G.MiniAurasApi = NewApi(registered)
		WowMock.FireEvent("ADDON_LOADED", "MiniAuras")

		fw.eq(#registered, 2, "packs registered once the API arrived")
	end)

	fw.it("gives up once MiniAuras has loaded, however its API turned out", function()
		local registered = {}

		LoadWith(nil)

		WowMock.FireEvent("ADDON_LOADED", "MiniAuras")

		-- Nothing can publish the API after MiniAuras' own load, so a later one is not ours.
		_G.MiniAurasApi = NewApi(registered)
		WowMock.FireEvent("ADDON_LOADED", "MiniAuras")

		fw.eq(#registered, 0, "the waiter stopped at the first MiniAuras load")
	end)

	fw.it("keeps waiting while some other addon loads", function()
		local registered = {}

		LoadWith(nil)

		_G.MiniAurasApi = NewApi(registered)
		WowMock.FireEvent("ADDON_LOADED", "SomethingElse")

		fw.eq(#registered, 0, "another addon's load is not the signal")

		WowMock.FireEvent("ADDON_LOADED", "MiniAuras")

		fw.eq(#registered, 2, "MiniAuras' own load is")
	end)

	fw.it("loads cleanly against a MiniAuras too old to know about voice packs", function()
		-- The API global exists from 5.0.0, but RegisterVoicePack only from 5.1.0, so calling
		-- it unguarded is what an older MiniAuras would break on.
		fw.no_error(function()
			LoadWith({ v1 = {} })
		end, "loading against an API without RegisterVoicePack")
	end)
end)
