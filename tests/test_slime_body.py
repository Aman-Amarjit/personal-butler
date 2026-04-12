"""Unit tests for SlimeBody physics and rendering"""

import pytest
import math
from src.ui.slime_body import SlimeBody, Vector2, AnimationState


class TestVector2:
    """Test Vector2 operations"""

    def test_vector_addition(self):
        v1 = Vector2(1, 2)
        v2 = Vector2(3, 4)
        result = v1 + v2
        assert result.x == 4
        assert result.y == 6

    def test_vector_multiplication(self):
        v = Vector2(2, 3)
        result = v * 2
        assert result.x == 4
        assert result.y == 6

    def test_vector_magnitude(self):
        v = Vector2(3, 4)
        assert v.magnitude() == 5.0

    def test_vector_normalize(self):
        v = Vector2(3, 4)
        normalized = v.normalize()
        assert abs(normalized.magnitude() - 1.0) < 0.001


class TestSlimeBody:
    """Test SlimeBody physics and animation"""

    def test_initialization(self):
        slime = SlimeBody((100, 100), size=50, color="#00FFFF")
        assert slime.position.x == 100
        assert slime.position.y == 100
        assert slime.base_size == 50
        assert slime.color == "#00FFFF"
        assert len(slime.deformation_points) == 32

    def test_animation_state_change(self):
        slime = SlimeBody((100, 100))
        assert slime.animation_state == AnimationState.IDLE

        slime.set_animation_state(AnimationState.LISTENING)
        assert slime.animation_state == AnimationState.LISTENING
        assert slime.jiggle_intensity == 0.1

    def test_physics_update(self):
        slime = SlimeBody((100, 100))
        slime.velocity = Vector2(10, 0)

        slime.update_physics(0.1)
        assert slime.position.x > 100  # Should move right

    def test_apply_force(self):
        slime = SlimeBody((100, 100))
        force = Vector2(100, 0)

        slime.apply_force(force, Vector2(0, 0))
        assert slime.velocity.x > 0

    def test_deformation_on_interaction(self):
        slime = SlimeBody((100, 100))
        initial_deformation = sum(slime.target_deformation)

        slime.deform_on_interaction((150, 100), intensity=0.5)
        new_deformation = sum(slime.target_deformation)

        assert new_deformation > initial_deformation

    def test_ripple_effect(self):
        slime = SlimeBody((100, 100))
        assert len(slime.ripples) == 0

        slime.apply_ripple_effect((100, 100), intensity=0.8)
        assert len(slime.ripples) == 1
        assert slime.ripples[0]['amplitude'] == 0.8

    def test_outline_points(self):
        slime = SlimeBody((100, 100), size=50)
        outline = slime.get_outline_points()

        assert len(outline) == 32
        for point in outline:
            assert isinstance(point, tuple)
            assert len(point) == 2

    def test_color_gradient(self):
        slime = SlimeBody((100, 100), color="#FF0000")
        base, highlight = slime.get_color_gradient()

        assert base == "#FF0000"
        assert highlight == "#FFFFFF"

    def test_reset(self):
        slime = SlimeBody((100, 100))
        slime.velocity = Vector2(50, 50)
        slime.current_size = 200

        slime.reset()
        assert slime.velocity.x == 0
        assert slime.velocity.y == 0
        assert slime.current_size == slime.base_size
