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
		(ontable orange)
		(clear orange)
		(ontable blue)
		(on green blue)
		(clear green)

		(ontable purple)
		(on red purple)
		(on yellow red)
		(clear yellow)
	)
	(:goal (and (handempty robot)
		(ontable purple)
		(clear purple)
		(ontable red)
		(on green red)
		(clear green)

		(ontable orange)
		(on blue orange)
		(clear blue)
		(ontable yellow)
		(clear yellow)
	))
)