(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable green)
		(on red green)
		(on purple red)
		(clear purple)
		(ontable yellow)
		(clear yellow)
		(ontable orange)
		(clear orange)

		(ontable blue)
		(clear blue)
	)
	(:goal (and (handempty robot)
		(ontable purple)
		(on red purple)
		(clear red)
		(ontable green)
		(clear green)
		(ontable orange)
		(clear orange)

		(ontable blue)
		(on yellow blue)
		(clear yellow)
	))
)