# This file is part of cloud-init. See LICENSE file for license information.


import logging

import pytest

from cloudinit.config.modules import ModuleDetails, Modules, _is_active
from cloudinit.config.schema import MetaSchema
from cloudinit.distros import ALL_DISTROS
from cloudinit.settings import FREQUENCIES
from tests.unittests.helpers import mock

M_PATH = "cloudinit.config.modules."


class TestModules:
    @pytest.mark.parametrize("frequency", FREQUENCIES)
    @pytest.mark.parametrize(
        "activate_by_schema_keys, cfg, active",
        [
            (None, {}, True),
            (None, {"module_name": {"x": "y"}}, True),
            ([], {"module_name": {"x": "y"}}, True),
            (["module_name"], {"module_name": {"x": "y"}}, True),
            (
                ["module_name", "other_module"],
                {"module_name": {"x": "y"}},
                True,
            ),
            (["module_name"], {"other_module": {"x": "y"}}, False),
            (
                ["x"],
                {"module_name": {"x": "y"}, "other_module": {"x": "y"}},
                False,
            ),
        ],
    )
    def test__is_inapplicable(
        self, activate_by_schema_keys, cfg, active, frequency
    ):
        module = mock.Mock()
        module.meta = MetaSchema(
            name="module_name",
            id="cc_module_name",
            title="title",
            description="description",
            distros=[ALL_DISTROS],
            examples=["example_0", "example_1"],
            frequency=frequency,
        )
        if activate_by_schema_keys is not None:
            module.meta["activate_by_schema_keys"] = activate_by_schema_keys
        module_details = ModuleDetails(
            module=module,
            name="name",
            frequency=frequency,
            run_args=[],
        )
        assert active == _is_active(module_details, cfg)

    @pytest.mark.parametrize("frequency", FREQUENCIES)
    @pytest.mark.parametrize("active", [True, False])
    def test_run_section(self, frequency, active, caplog, mocker):
        mocker.patch(M_PATH + "_is_active", return_value=active)

        mods = Modules(
            init=mock.Mock(), cfg_files=mock.Mock(), reporter=mock.Mock()
        )
        mods._cached_cfg = {}
        raw_name = "my_module"
        module = mock.Mock()
        module.meta = MetaSchema(
            name=raw_name,
            id=f"cc_{raw_name}",
            title="title",
            description="description",
            distros=[ALL_DISTROS],
            examples=["example_0", "example_1"],
            frequency=frequency,
        )
        module_details = ModuleDetails(
            module=module,
            name=raw_name,
            frequency=frequency,
            run_args=["<arg>"],
        )
        mocker.patch.object(
            mods,
            "_fixup_modules",
            return_value=[module_details],
        )
        m_run_modules = mocker.patch.object(mods, "_run_modules")

        assert mods.run_section("not_matter")
        if active:
            assert [
                mock.call([list(module_details)])
            ] == m_run_modules.call_args_list
            assert not caplog.text
        else:
            assert [mock.call([])] == m_run_modules.call_args_list
            assert (
                logging.INFO,
                (
                    f"Skipping modules '{raw_name}' because no applicable"
                    " config is provided."
                ),
            ) == caplog.record_tuples[-1][1:]
